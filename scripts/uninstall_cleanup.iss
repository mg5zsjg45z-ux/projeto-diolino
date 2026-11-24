; Native Inno Setup cleanup. Never run shell scripts or scan for personal files.
; Compile-time overrides are used only by the isolated uninstall integration test.
#ifndef CleanupDataRoot
  #define CleanupDataRoot "{localappdata}\ProjetoDiolino"
#endif
#ifndef CleanupProgramRoot
  #define CleanupProgramRoot "{localappdata}\Programs\Diolino"
#endif
#ifndef CleanupStartupRoot
  #define CleanupStartupRoot "{userstartup}"
#endif
#ifndef CleanupUserRoot
  #define CleanupUserRoot "{userprofile}"
#endif

[Code]
function DiolinoProcessRunning: Boolean;
var
  Locator, Services, Processes, Item: Variant;
  I: Integer;
  Exe, Root, UserRoot, CommandLine: String;
begin
  Result := False;
  Root := Lowercase(AddBackslash(ExpandConstant('{#CleanupProgramRoot}')));
  UserRoot := Lowercase(AddBackslash(ExpandConstant('{#CleanupUserRoot}')));
  Locator := CreateOleObject('WbemScripting.SWbemLocator');
  Services := Locator.ConnectServer('', 'root\CIMV2');
  Processes := Services.ExecQuery('SELECT ExecutablePath,CommandLine FROM Win32_Process WHERE Name=''Diolino.exe''');
  for I := 0 to Processes.Count - 1 do begin
    Item := Processes.ItemIndex(I);
    if not VarIsNull(Item.ExecutablePath) then begin
      Exe := Item.ExecutablePath;
      Exe := Lowercase(Exe);
      CommandLine := '';
      if not VarIsNull(Item.CommandLine) then CommandLine := Item.CommandLine;
      if (Pos(Root, Exe) = 1) or
         ((Pos(UserRoot, Exe) = 1) and (Pos('--data-dir', Lowercase(CommandLine)) = 0)) then begin
        Result := True;
        Exit;
      end;
    end;
  end;
end;

function StopDiolinoCompanion: Boolean;
var
  LinkPath, Arguments, StartScript, SourceRoot, ExpectedServer, CommandLine: String;
  Shell, Link, Locator, Services, Processes, Item: Variant;
  I, FirstQuote, LastQuote, Ignored, Attempt: Integer;
begin
  Result := True;
  LinkPath := ExpandConstant('{#CleanupStartupRoot}\Diolino - acesso iPhone.lnk');
  if not FileExists(LinkPath) then Exit;
  Shell := CreateOleObject('WScript.Shell');
  Link := Shell.CreateShortcut(LinkPath);
  Arguments := Link.Arguments;
  FirstQuote := Pos('"', Arguments);
  if FirstQuote = 0 then Exit;
  Arguments := Copy(Arguments, FirstQuote + 1, Length(Arguments));
  LastQuote := Pos('"', Arguments);
  if LastQuote = 0 then Exit;
  StartScript := Copy(Arguments, 1, LastQuote - 1);
  if Lowercase(ExtractFileName(StartScript)) <> 'start_mobile.ps1' then Exit;
  SourceRoot := ExtractFileDir(ExtractFileDir(StartScript));
  ExpectedServer := Lowercase('"' + AddBackslash(SourceRoot) + 'mobile_server.py"');
  Locator := CreateOleObject('WbemScripting.SWbemLocator');
  Services := Locator.ConnectServer('', 'root\CIMV2');
  Processes := Services.ExecQuery('SELECT * FROM Win32_Process WHERE Name=''pythonw.exe'' OR Name=''python.exe''');
  for I := 0 to Processes.Count - 1 do begin
    Item := Processes.ItemIndex(I);
    if not VarIsNull(Item.CommandLine) then begin
      CommandLine := Item.CommandLine;
      // Both a venv launcher and its base-Python child may have this exact script.
      if Pos(ExpectedServer, Lowercase(CommandLine)) > 0 then Ignored := Item.Terminate(0);
    end;
  end;
  for Attempt := 1 to 20 do begin
    Sleep(100);
    Result := True;
    Processes := Services.ExecQuery('SELECT CommandLine FROM Win32_Process WHERE Name=''pythonw.exe'' OR Name=''python.exe''');
    for I := 0 to Processes.Count - 1 do begin
      Item := Processes.ItemIndex(I);
      if not VarIsNull(Item.CommandLine) then begin
        CommandLine := Item.CommandLine;
        if Pos(ExpectedServer, Lowercase(CommandLine)) > 0 then Result := False;
      end;
    end;
    if Result then Exit;
  end;
end;

function InitializeUninstall: Boolean;
begin
  Result := False;
  try
    if DiolinoProcessRunning then begin
      if not UninstallSilent then
        MsgBox('O Diolino ainda está aberto. Use "Sair completamente" no aplicativo ou na bandeja e execute o desinstalador novamente.', mbError, MB_OK);
      Log('Desinstalação cancelada: Diolino em execução.');
      Exit;
    end;
  except
    if not UninstallSilent then
      MsgBox('Não foi possível verificar se o Diolino está fechado. Nenhum dado foi apagado. Feche o aplicativo e tente novamente.', mbError, MB_OK);
    Exit;
  end;
  if UninstallSilent then begin
    // Silent deletion also requires the explicit data-removal flag.
    if ExpandConstant('{param:PURGEDATA|0}') <> '1' then begin
      Log('Desinstalação silenciosa exige /PURGEDATA=1. Nenhum dado foi apagado.');
      Exit;
    end;
  end else begin
    if MsgBox('Desinstalar o Diolino e apagar permanentemente os dados locais deste usuário neste PC?' + #13#10 + #13#10 +
      'Serão apagados o banco SQLite, backups internos, registros de saúde, anotações, configurações, credenciais locais e arquivos auxiliares da pasta:' + #13#10 +
      ExpandConstant('{#CleanupDataRoot}') + #13#10 + #13#10 +
      'O acesso local pelo iPhone será encerrado e seus atalhos removidos. Arquivos exportados ou copiados para outras pastas, dados de outros usuários e dados do site não serão apagados.' + #13#10 + #13#10 +
      'A exclusão comum do Windows não é uma garantia de apagamento forense. Deseja continuar?',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2) <> IDYES then Exit;
  end;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Root: String;
begin
  if CurUninstallStep = usUninstall then begin
    if not StopDiolinoCompanion then
      RaiseException('Não foi possível encerrar o acesso local pelo iPhone. Encerre-o e execute novamente o desinstalador.');
    // Only the fixed application data directory; DelTree does not follow reparse points.
    Root := ExpandConstant('{#CleanupDataRoot}');
    if DirExists(Root) then
      if not DelTree(Root, True, True, True) then
        RaiseException('Não foi possível apagar todos os dados de ' + Root + '. Feche os programas que usam a pasta e tente novamente.');
    DeleteFile(ExpandConstant('{#CleanupStartupRoot}\Diolino - acesso iPhone.lnk'));
    DeleteFile(ExpandConstant('{#CleanupStartupRoot}\Diolino.lnk'));
    DeleteFile(ExpandConstant('{#CleanupUserRoot}\Desktop\Diolino.lnk'));
    DeleteFile(ExpandConstant('{#CleanupUserRoot}\OneDrive\Desktop\Diolino.lnk'));
    Log('Pasta de dados locais do Diolino removida. Arquivos externos e dados online preservados.');
  end;
end;
