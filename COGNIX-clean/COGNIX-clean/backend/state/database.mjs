export function adapter(db) {
 return {
  prepare(sql) {
   return {
    bind(...args) {
     return {
      async first() { return db.prepare(sql).get(...args) || null; },
      async run() { const r = db.prepare(sql).run(...args); return {meta:{changes:Number(r.changes)}}; }
     };
    }
   };
  }
 };
}
