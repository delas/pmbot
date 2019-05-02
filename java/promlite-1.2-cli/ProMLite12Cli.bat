cd "C:\Users\andbur\PycharmProjects\pmbot\java\promlite-1.2-cli"
@GOTO start

:add
 @set X=%X%;%1
 @GOTO :eof

:start
@set X=.\dist\ProM-Framework.jar
@set X=%X%;.\dist\ProM-Contexts.jar
@set X=%X%;.\dist\ProM-Models.jar
@set X=%X%;.\dist\ProM-Plugins.jar

@for /R .\lib %%I IN ("*.jar") DO @call :add .\lib\%%~nI.jar


"C:\Program Files\Java\jre1.8.0_212\bin\java.exe" -da -Xmx4G -XX:MaxPermSize=256m -classpath "%X%" -Djava.library.path=.//lib -Djava.util.Arrays.useLegacyMergeSort=true org.processmining.contexts.cli.CLI %1 %2

set X=
