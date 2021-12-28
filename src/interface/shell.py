import cmd
import sys
import shlex

class NoteSearchShell(cmd.Cmd):
    intro = 'Welcom to notes-search shell.   Type help or ? to list commands.\n'
    prompt = '(notes) '
    history = None

    def do_search(self, arg):
        """
        Do basic note search.
        """
        arg_parsed = shlex.split(arg)
        print(f"Performing a search on: {arg_parsed}")
        
    def do_quit(self, _):
        """
        Quits the programme.
        """
        sys.exit(0)

if __name__ == '__main__':
    NoteSearchShell().cmdloop()