"""Exercise the packaged skill in isolated temporary project directories."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
HELPER=ROOT/'integration/plugin/skills/project-blocks/scripts/project_blocks.py'
PROGRESS=HELPER.with_name('progress.py')

class Integration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='project-blocks-integration-')
        self.parent=Path(self.temp.name)
        self.a,self.b=self.parent/'甲 project',self.parent/'乙 project'
        self.a.mkdir();self.b.mkdir()

    def tearDown(self):
        for state in self.parent.rglob('.runtime.json'):
            pid=json.loads(state.read_text(encoding='utf-8')).get('pid')
            if pid:
                try:os.kill(pid,signal.SIGTERM)
                except OSError:pass
        # Only the TemporaryDirectory allocated above is recursively removed.
        import time
        time.sleep(.2)
        self.temp.cleanup()

    def run_helper(self,root,*extra,success=True):
        proc=subprocess.run([sys.executable,str(HELPER),'ensure','--project-root',str(root),*extra],capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONUTF8':'1'})
        self.assertEqual(proc.returncode==0,success,proc.stderr)
        return json.loads(proc.stdout if success else proc.stderr)

    def get(self,url,path):
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url+path,timeout=3) as r:return json.load(r)

    def test_independent_services_reuse_and_preserve(self):
        a=self.run_helper(self.a,'--title','项目甲','--start')
        b=self.run_helper(self.b,'--title','项目乙','--start')
        self.assertTrue(a['created']);self.assertTrue(b['created']);self.assertNotEqual(a['url'],b['url'])
        da,db=Path(a['dataFile']),Path(b['dataFile'])
        self.assertEqual(da.parent.parent.parent,self.a)
        self.assertEqual(self.get(a['url'],'/api/project')['project']['title'],'项目甲')
        self.assertEqual(self.get(b['url'],'/api/project')['project']['title'],'项目乙')
        self.assertEqual(self.get(a['url'],'/api/info')['dataFile'],str(da))
        project=json.loads(da.read_text(encoding='utf-8'));project['nodes'][0]['title']='用户修改';project['nodes'][0]['x']=987
        da.write_text(json.dumps(project,ensure_ascii=False),encoding='utf-8')
        app=self.a/'project-blocks/app/blocks.css';app.write_text(app.read_text(encoding='utf-8')+'\n/* user customization */',encoding='utf-8')
        prior=(da.read_bytes(),app.read_bytes())
        again=self.run_helper(self.a,'--title','不能覆盖标题','--start')
        self.assertFalse(again['created']);self.assertTrue(again['reused']);self.assertEqual(again['url'],a['url'])
        self.assertEqual(prior,(da.read_bytes(),app.read_bytes()))
        for root in [self.a,self.b]:
            self.assertTrue((root/'project-blocks/start.py').exists())
            self.assertTrue((root/'project-blocks/runtime.py').exists())
            self.assertTrue((root/'project-blocks/启动.cmd').exists())
            self.assertFalse((root/'project-blocks/data/example.project.json').exists())
        self.assertTrue(all(n['workflow']['status']=='todo' for n in self.get(b['url'],'/api/project')['project']['nodes']))

    def test_plan_and_corrupt_project_preservation(self):
        plan=self.parent/'plan.json'
        plan.write_text(json.dumps(dict(title='真实计划',nodes=[dict(id='ui',title='界面',type='route'),dict(id='qa',title='验收',type='ending')],edges=[{'from':'ui','to':'qa'}])),encoding='utf-8')
        result=self.run_helper(self.a,'--plan',str(plan))
        data=Path(result['dataFile']);project=json.loads(data.read_text(encoding='utf-8'))
        self.assertEqual(project['title'],'真实计划');self.assertEqual(project['nodes'][0]['choices'][0]['target'],'qa')
        data.write_text('{ invalid',encoding='utf-8');before=data.read_bytes()
        self.run_helper(self.a,success=False);self.assertEqual(data.read_bytes(),before)
        self.run_helper(Path.home(),success=False)

    def test_progress_commands_and_backed_up_upgrade(self):
        result=self.run_helper(self.a,'--start')
        root=self.a/'project-blocks';data=Path(result['dataFile'])
        original=data.read_bytes()
        css=root/'app/blocks.css';css.write_text('/* user customization */',encoding='utf-8')
        upgrade=self.run_helper(self.a,'--upgrade','--start')
        self.assertEqual(data.read_bytes(),original)
        self.assertEqual((Path(upgrade['upgradeBackup'])/'app/blocks.css').read_text(),'/* user customization */')
        def progress(*args,success=True):
            proc=subprocess.run([sys.executable,str(PROGRESS),'--project-root',str(self.a),'--node','requirements',*args],capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONUTF8':'1'})
            self.assertEqual(proc.returncode==0,success,proc.stderr)
            return proc
        progress('--run',sys.executable,'-c','import time; time.sleep(16)')
        activity=self.get(result['url'],'/api/activity')['nodes']['requirements']
        self.assertEqual(activity['status'],'review')
        self.assertEqual(json.loads(data.read_bytes())['nodes'][0]['workflow']['status'],'review')
        progress('--run',sys.executable,'-c','raise SystemExit(2)',success=False)
        self.assertEqual(self.get(result['url'],'/api/activity')['nodes']['requirements']['status'],'blocked')
        progress('--status','done',success=False)
        progress('--status','done','--evidence','实际测试：成功命令、失败命令与心跳已验证')
        self.assertEqual(json.loads(data.read_bytes())['nodes'][0]['workflow']['status'],'done')

if __name__=='__main__':unittest.main(verbosity=2)
