// Device enrollment is available only inside the authenticated account.
(() => {
 const original=renderMore;
 renderMore=async function(){
  await original();
  const card=el('section',undefined,'card device-sync-card');card.append(el('h2','Sincronização com o Windows'));
  card.append(el('p','Conecte cada computador uma vez. Depois, o aplicativo sincroniza os registros pela internet a cada minuto enquanto estiver aberto, inclusive na bandeja. O site pode estar fechado.'));
  const label=el('label','Nome deste computador'),name=el('input');name.maxLength=100;name.value='Meu Windows';label.append(name);card.append(label);
  const button=el('button','Gerar autorização para o Windows','primary'),status=el('p','','muted');status.setAttribute('role','status');card.append(button,status);
  card.append(el('p','No Windows, abra “Dados e backup → Conectar site pela internet” e importe o arquivo .diolinoconnect. Ele contém uma credencial de acesso: apague-o após importar e gere outra autorização para cada PC. A credencial instalada fica protegida pela conta do Windows.','muted'));
  card.append(el('p','Transfere registros ativos, agenda, planos, etapas e anotações em texto simples. Diferenças dos dois lados exigem revisão no Windows. Não transfere cartões FSRS, anexos da Biblioteca, exclusões, credenciais do iCloud, formatação das notas ou um cronômetro em andamento.','muted'));
  button.onclick=async()=>{
   button.disabled=true;status.textContent='Preparando autorização…';
   try{
    const connection=await api('/api/devices',{action:'create',label:name.value});
    download(JSON.stringify(connection,null,2),'diolino-windows.diolinoconnect','application/json;charset=utf-8');
    status.textContent='Autorização gerada. Importe o arquivo no Windows para concluir a conexão.';
    await drawDevices();
   }catch(error){status.textContent='Não foi possível conectar: '+error.message;}finally{button.disabled=false;}
  };
  const list=el('div');card.append(list);
  async function drawDevices(){
   const data=await api('/api/devices');list.replaceChildren();
   const current=data.devices.filter(device=>!device.revoked_at&&Date.parse(device.expires_at)>Date.now());
   if(!current.length){list.append(el('p','Nenhum computador autorizado.','muted'));return;}
   list.append(el('h3','Computadores autorizados'));
   for(const device of current){
    const row=el('div',undefined,'row'),text=el('div');text.append(el('strong',device.label),el('p','Autorização até '+new Date(device.expires_at).toLocaleDateString('pt-BR'),'muted'));
    const revoke=el('button','Revogar '+device.label);revoke.onclick=async()=>{
     revoke.disabled=true;try{await api('/api/devices',{action:'revoke',id:device.id});await drawDevices();status.textContent='Autorização revogada. Os registros já transferidos permanecem nos dispositivos.';}catch(error){status.textContent=error.message;revoke.disabled=false;}
    };
    row.append(text,revoke);list.append(row);
   }
  }
  more.prepend(card);try{await drawDevices();}catch(error){status.textContent='Não foi possível consultar as conexões: '+error.message;}
 };
})();
