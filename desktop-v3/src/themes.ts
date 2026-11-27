export const themes = {
 paper: {label:'Papel · sálvia suave',study:'#495f74',exercise:'#52654e',sleep:'#625676',weight:'#815d39',attention:'#85513e',fg:'#514e45',grid:'#ddd7cb'},
 xp: {label:'XP · Luna azul',study:'#175eae',exercise:'#397c24',sleep:'#287ca2',weight:'#9a6509',attention:'#a35405',fg:'#3d5068',grid:'#cad6e6'},
 classic: {label:'Clássico · 95/98',study:'#000080',exercise:'#006400',sleep:'#006b80',weight:'#805500',attention:'#800000',fg:'#222222',grid:'#b5b5b5'},
 royale: {label:'Royale · escuro',study:'#86baff',exercise:'#9bd66a',sleep:'#73d2f1',weight:'#ffd184',attention:'#ffbb75',fg:'#c1cfe2',grid:'#344a66'},
} as const;
export type Theme = keyof typeof themes;
export function loadTheme():Theme {
 try {
  const saved=localStorage.getItem('diolino-theme');
  if(saved==='paper'||saved==='xp'||saved==='classic'||saved==='royale')return saved;
 }catch{/* unavailable storage: use default */}
 return 'paper';
}
export function saveTheme(theme:Theme){
 try{localStorage.setItem('diolino-theme',theme)}catch{/* visual preferences are optional */}
}
