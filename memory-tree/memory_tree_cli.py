import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

from memory_tree.agent import run_memory_agent

console = Console()

def main():
    console.print("[bold cyan]Welcome to the Obsidian-style Memory Tree CLI for New Reactor[/bold cyan]")
    console.print("Type 'exit' or 'quit' to leave. Type 'clear' to clear the screen.\n")

    # In a fully integrated version, the model selection would be read from new_reactor's config.json
    model_name = "gpt-4o"
    
    while True:
        try:
            user_input = Prompt.ask("[bold green]User[/bold green]")
            if user_input.lower() in ['exit', 'quit']:
                console.print("[yellow]Goodbye![/yellow]")
                break
            elif user_input.lower() == 'clear':
                console.clear()
                continue
            
            if not user_input.strip():
                continue
                
            with console.status("[bold blue]Thinking and retrieving context...[/bold blue]"):
                # Run the agent
                response = run_memory_agent(user_input, model_name=model_name, update_memory=True)
                
            console.print("\n[bold magenta]Agent:[/bold magenta]")
            console.print(Markdown(response))
            console.print("-" * 40)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]An error occurred:[/bold red] {e}")

if __name__ == "__main__":
    main()
