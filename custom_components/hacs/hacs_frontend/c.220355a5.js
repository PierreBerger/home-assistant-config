import{L as o}from"./main-8113c4f2.js";const a=()=>import("./c.9afaa94b.js"),i=(i,l,n)=>new Promise(m=>{const r=l.cancel,c=l.confirm;o(i,"show-dialog",{dialogTag:"dialog-box",dialogImport:a,dialogParams:{...l,...n,cancel:()=>{m(!(null==n||!n.prompt)&&null),r&&r()},confirm:o=>{m(null==n||!n.prompt||o),c&&c(o)}}})}),l=(o,a)=>i(o,a),n=(o,a)=>i(o,a,{confirmation:!0});export{l as a,n as s};
