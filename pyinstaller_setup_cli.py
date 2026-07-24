r'''
    C:\Users\05rem\Documents\python\venvs\gamegear\Lib\site-packages\
    pywin32_system32 *.dll

    TODO:
        --version-file?
        --menifest

    USING UPX:
        UPXdir = "D:/Program Files/upx-3.95-win64"
        "--upx-dir={}".format(UPXdir)
'''

import PyInstaller.__main__
import sys, os

DistBasePath     = '/home/leo/.pyvirtenvs/msty_like'
ProgramBuildPath = '/home/leo/.pyvirtenvs/msty_like/heavy'
programName      = 'msty_like_cli'

executionList = [
    # '--add-data=sessions:sessions',
    # '--add-data=prompts:prompts',
    # '--add-data=plugins:plugins',
    # '--add-data=config.json:config.json',
    # '--add-data=toolz.py:toolz.py',
    '--name=msty_like_cli',
    '--add-data=repl_settings.py:repl_settings.py',
    '--add-data=subagents.py:subagents.py',
    '--window'
    '--clean']

executionList.append('{}/{}'.format(ProgramBuildPath, 'repl.py'))
PyInstaller.__main__.run(executionList)

# ln -s "/home/leo/.pyvirtenvs/passman/config.rc" "/home/leo/.pyvirtenvs/passman/dist/pass_man/config.rc"
# ln -s "/home/leo/.pyvirtenvs/passman/data.db" "/home/leo/.pyvirtenvs/passman/dist/pass_man/data.db"
# ln -s "/home/leo/.pyvirtenvs/passman/data.file" "/home/leo/.pyvirtenvs/passman/dist/pass_man/data.file"



