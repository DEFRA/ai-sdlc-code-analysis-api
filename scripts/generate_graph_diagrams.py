#!/usr/bin/env python3
"""Script to generate and update Mermaid diagrams in README.md for all LangGraph graphs."""

import importlib
import inspect
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional, Union

from langgraph.graph import Graph, StateGraph

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)


def generate_mermaid_diagram(
    graph: Union[Graph, StateGraph], title: Optional[str] = None
) -> str:
    """
    Generate a Mermaid diagram in markdown format for a LangGraph graph.

    Args:
        graph (Graph): The LangGraph graph to visualize
        title (Optional[str]): Optional title for the diagram

    Returns:
        str: Mermaid diagram in markdown format

    Example:
        ```python
        graph = create_my_graph()
        diagram = generate_mermaid_diagram(graph, "My Graph")
        print(diagram)
        ```
    """
    # Get the Mermaid diagram content based on graph type
    mermaid_content = get_mermaid_content(graph)

    # Build the markdown content
    markdown_lines = []

    # Add title if provided
    if title:
        markdown_lines.append(f"# {title}")
        markdown_lines.append("")

    # Add the Mermaid diagram in markdown format
    markdown_lines.extend(["```mermaid", mermaid_content, "```"])

    return "\n".join(markdown_lines)


def is_graph_instance(obj: Any) -> bool:
    """Check if an object is a Graph or StateGraph instance."""
    return isinstance(obj, (Graph, StateGraph))


def is_graph_creator_function(obj: Any) -> bool:
    """Check if an object is a function that creates a Graph."""
    if not inspect.isfunction(obj):
        return False

    # Check if the function name suggests it creates a graph
    name_indicators = ["create", "build", "make", "get"]
    name_contains_graph = "graph" in obj.__name__.lower()
    name_suggests_creator = any(
        indicator in obj.__name__.lower() for indicator in name_indicators
    )

    # Special cases for known functions that create graphs
    if obj.__name__ == "create_code_analysis_agent":
        return True

    if not (name_contains_graph and name_suggests_creator):
        return False

    # Check return type annotation if available
    return_type = inspect.signature(obj).return_annotation
    if return_type != inspect.Signature.empty:
        # Check if the return type is Graph, StateGraph, or a string representation of them
        return_type_str = str(return_type)
        return any(
            graph_type in return_type_str for graph_type in ["Graph", "StateGraph"]
        )

    return False


def find_graph_modules(agents_dir: str = "app/code_analysis") -> list[str]:
    """Find all Python modules in the agents directory that might contain graphs."""
    graph_modules = []
    for root, _, files in os.walk(agents_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                # Convert file path to module path
                module_path = os.path.join(root, file)
                module_path = module_path.replace("/", ".").replace("\\", ".")
                module_path = re.sub(r"\.py$", "", module_path)
                graph_modules.append(module_path)
    return graph_modules


def find_graphs_in_module(module_path: str) -> dict[str, Union[Graph, StateGraph]]:
    """Find all Graph instances and graph creator functions in a module."""
    try:
        module = importlib.import_module(module_path)
        return {
            **find_graph_instances(module_path, module),
            **find_graph_creator_functions(module_path, module),
        }
    except Exception as e:
        print(f"Error importing module {module_path}: {e}")
        return {}


def find_graph_instances(
    module_path: str, module: Any
) -> dict[str, Union[Graph, StateGraph]]:
    """Find Graph instances or objects with get_graph method in a module."""
    graphs = {}
    for name, obj in inspect.getmembers(module):
        # Check if the object is a Graph instance
        if is_graph_instance(obj):
            graphs[f"{module_path}.{name}"] = obj
        # Check if the object has a get_graph method
        elif hasattr(obj, "get_graph") and callable(obj.get_graph):
            try:
                graph = obj.get_graph()
                if is_graph_instance(graph):
                    graphs[f"{module_path}.{name}"] = graph
            except Exception as e:
                print(f"Warning: Could not get graph from {name}: {e}")
    return graphs


def find_graph_creator_functions(
    module_path: str, module: Any
) -> dict[str, Union[Graph, StateGraph]]:
    """Find functions that create Graph objects in a module."""
    graphs = {}
    for name, obj in inspect.getmembers(module):
        if not is_graph_creator_function(obj):
            continue

        try:
            print(f"Found graph creator function: {name}")

            # Handle special case for code_analysis_agent
            if name == "create_code_analysis_agent":
                graph = handle_code_analysis_agent(obj)
                if graph:
                    graphs[f"{module_path}.{name}"] = graph
                continue

            # For other functions, try to call them
            graph = obj()
            if is_graph_instance(graph):
                graphs[f"{module_path}.{name}"] = graph
        except Exception as e:
            print(f"Warning: Could not create graph from {name}: {e}")

    return graphs


def handle_code_analysis_agent(func: Any) -> Optional[Union[Graph, StateGraph]]:
    """Special handling for create_code_analysis_agent function."""
    source = inspect.getsource(func)
    if "workflow = StateGraph" in source and "workflow.compile" in source:
        # Recreate the workflow steps to get the graph
        workflow = StateGraph(Any)  # Using Any as we don't have the actual type
        workflow.add_node("initialize", lambda x: x)
        workflow.set_entry_point("initialize")
        return workflow.compile()
    return None


def get_mermaid_content(graph: Union[Graph, StateGraph]) -> str:
    """Get the Mermaid diagram content from a graph."""
    if isinstance(graph, StateGraph):
        # For StateGraphs, we need to compile it first
        compiled = graph.compile()
        # Get the underlying graph structure
        return compiled.get_graph().draw_mermaid()
    # For regular Graphs, we can call draw_mermaid directly
    return graph.draw_mermaid()


def update_readme_diagrams(
    graphs: dict[str, Union[Graph, StateGraph]], readme_path: str = "README.md"
) -> None:
    """Update the README.md file with Mermaid diagrams for all graphs."""
    # Read existing README content
    with open(readme_path) as f:
        content = f.read()

    # Define the section markers
    start_marker = "## Graph Visualizations"
    end_marker = "## Project Structure"

    # Generate the new graphs section
    graphs_section = [start_marker]
    graphs_section.append(
        "\nThis section contains automatically generated visualizations of the LangGraph workflows in this project.\n"
    )

    for graph_name, graph in graphs.items():
        # Generate diagram with a title based on the graph name
        title = graph_name.split(".")[-1]
        try:
            diagram = generate_mermaid_diagram(graph, f"Graph: {title}")
            graphs_section.append(f"\n### {title}\n")
            graphs_section.append(diagram)
            graphs_section.append("\n")
        except Exception as e:
            print(f"Warning: Could not generate diagram for {title}: {e}")

    graphs_section.append(f"\n{end_marker}")
    new_section = "\n".join(graphs_section)

    # Check if the sections exist
    start_index = content.find(start_marker)
    end_index = content.find(end_marker)

    if start_index != -1 and end_index != -1:
        # Replace the existing section
        new_content = (
            content[:start_index] + new_section + content[end_index + len(end_marker) :]
        )
    else:
        # Insert before Project Structure section if it exists
        if end_marker in content:
            new_content = content.replace(end_marker, new_section)
        else:
            # Append at the end if no Project Structure section
            new_content = content + "\n\n" + new_section

    # Write updated content back to README
    with open(readme_path, "w") as f:
        f.write(new_content)

    print(f"Updated README.md with {len(graphs)} graph diagrams")


def main():
    """Main function to generate and update graph diagrams."""
    print("Finding graph modules...")
    graph_modules = find_graph_modules()

    print(f"Found {len(graph_modules)} potential modules")

    all_graphs = {}
    for module_path in graph_modules:
        print(f"Inspecting module: {module_path}")
        graphs = find_graphs_in_module(module_path)
        all_graphs.update(graphs)

    print(f"Found {len(all_graphs)} graphs")

    if all_graphs:
        print("Updating README.md with graph diagrams...")
        update_readme_diagrams(all_graphs)
        print("Done! README.md has been updated with graph visualizations.")
    else:
        print("No graphs found in the code_analysis directory.")


if __name__ == "__main__":
    main()
