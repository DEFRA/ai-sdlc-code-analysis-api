import logging

from app.code_analysis.agents.nodes.code_chunker.parsers import CSharpParser
from app.code_analysis.agents.nodes.code_chunker.utils.parser_utils import ParserManager

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

parser_manager = ParserManager(logger)
parser = parser_manager.parsers["C#"]
csharp_parser = CSharpParser(logger)

sample_code = """
/// <summary>
/// This is an XML doc comment
/// </summary>
public class Test {}
"""

result = csharp_parser.extract_elements(sample_code, parser)
print("Comments found:", result["comments"])
