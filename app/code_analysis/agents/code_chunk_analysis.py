from langgraph.graph import END, START, StateGraph

from app.code_analysis.agents.nodes.analyse_code_chunk import analyse_code_chunk
from app.code_analysis.agents.states.code_chuck_analysis import CodeChunkAnalysisState

code_chunk_analysis_builder = StateGraph(CodeChunkAnalysisState)

code_chunk_analysis_builder.add_node("analyse_code_chunk", analyse_code_chunk)

code_chunk_analysis_builder.add_edge(START, "analyse_code_chunk")
code_chunk_analysis_builder.add_edge("analyse_code_chunk", END)

code_chunk_analysis = code_chunk_analysis_builder.compile()
