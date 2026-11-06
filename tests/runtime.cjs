const path=require('node:path');
const os=require('node:os');
const fs=require('node:fs');
const bundle=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies');
exports.load=name=>{
  try{return require(name);}catch(error){
    if(error.code!=='MODULE_NOT_FOUND')throw error;
    const fallback=path.join(bundle,'node/node_modules',name);
    if(fs.existsSync(fallback))return require(fallback);
    throw Error(`Missing development dependency ${name}. Run npm install.`);
  }
};
const bundledPython=path.join(bundle,'python',process.platform==='win32'?'python.exe':'bin/python3');
exports.python=process.env.PYTHON || (fs.existsSync(bundledPython)?bundledPython:(process.platform==='win32'?'python':'python3'));
