import type { Metadata } from 'next';
export const metadata: Metadata={title:'Diolino — controle pessoal',description:'Rotina, saúde e planejamento em uma conta privada.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="pt-BR"><body>{children}</body></html>}
