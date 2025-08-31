"""
Example research agent for DeepAgents with optional web search providers.

This module defines a simple research agent powered by the DeepAgents framework.
It exposes an ``internet_search`` tool that can search the web using either
Tavily or the Google Programmable Search (Custom Search JSON API). At runtime
the agent will automatically prefer Google search when the required
environment variables and dependencies are available. Otherwise it will
fall back to Tavily when a ``TAVILY_API_KEY`` is configured, and finally
return a helpful error message if no search provider is configured.

The remainder of the file mirrors the original ``research_agent.py`` from the
``deepagents`` repository. It includes prompts for both a researcher and a
critique sub‑agent, as well as instructions for composing a final report. The
agent is constructed via :func:`deepagents.create_deep_agent` with both
sub‑agents and the ``internet_search`` tool.
"""

import os
from typing import Literal, Any, Optional, Dict, List

# Attempt to import Tavily client. This dependency is optional so that the
# example can still run without the tavily‑python package being installed.
try:
    from tavily import TavilyClient # type: ignore
except Exception:
    TavilyClient = None # type: ignore

# Attempt to import requests for Google search. If requests is not
# installed then Google search will be disabled.
try:
    import requests # type: ignore
except Exception:
    requests = None # type: ignore


from deepagents import create_deep_agent, SubAgent
from langchain.chat_models import init_chat_model
 
# Tavily API configuration. If both the dependency and API key are provided
# a Tavily client will be instantiated and reused. Otherwise ``tavily_client``
# remains ``None`` and Tavily search will be skipped.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily_client: Optional[Any] = None
if TavilyClient and TAVILY_API_KEY:
    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY) # type: ignore
    except Exception:
        tavily_client = None

# Google Custom Search configuration. Two environment variables are used to
# configure Google search: ``GOOGLE_API_KEY`` and ``GOOGLE_CSE_ID``. The
# ``requests`` library must also be available. If any of these are missing
# Google search will be skipped.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

def _google_custom_search(
    query: str,
    max_results: int = 5,
    include_raw_content: bool = False,
    topic: Literal["general", "news", "finance"] = "general",
) -> Optional[Dict[str, Any]]:
    """Execute a Google Custom Search API query.
    This helper returns results in a structure similar to Tavily's search API.
    Each result item contains a ``url``, ``title`` and ``content`` (snippet).

    Parameters
    ----------
    query : str
        The search query.
    max_results : int, optional
        Maximum number of results to return, by default 5. Google limits this
        to 10 per request.
    include_raw_content : bool, optional
        Unused for Google search; included for signature compatibility.
    topic : Literal["general", "news", "finance"], optional
        Unused for Google search; included for signature compatibility.

    Returns
    -------
    Optional[dict]
        A dictionary with a ``results`` key on success or ``None`` if Google
        search cannot be executed (e.g. misconfiguration or missing dependency).
    """

    # Ensure configuration and requests are available
    if not (GOOGLE_API_KEY and GOOGLE_CSE_ID and requests):
        return None
    try:
        url = "https://www.googleapis.com/customsearch/v1"
         # Google API accepts up to 10 results per request
         num = max_results if max_results <= 10 else 10
         params = {
             "key": GOOGLE_API_KEY,
             "cx": GOOGLE_CSE_ID,
             "q": query,
             "num": num,
         }
         resp = requests.get(url, params=params, timeout=10) # type: ignore
         resp.raise_for_status() # type: ignore
         data: Dict[str, Any] = resp.json() # type: ignore
         items: List[Dict[str, Any]] = []
         for item in data.get("items", []):
             items.append(
                 {
                    "url": item.get("link"),
                    "title": item.get("title"),
                    # Use the snippet as content; Google does not provide full
                    # article text via the public API.
                    "content": item.get("snippet"),
                 }
             )
         return {"results": items}
    except Exception as exc: # pragma: no cover - network/remote failures
        # Return an error structure so that the agent can surface issues
        return {"error": str(exc), "query": query}



# Search tool to use to do research
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> Dict[str, Any]:
    """Run a web search using the best available provider.

    The function first attempts to use Google Programmable Search if the
    ``GOOGLE_API_KEY`` and ``GOOGLE_CSE_ID`` environment variables are set and
    the ``requests`` library is installed. If Google search is not available
    it falls back to Tavily search (if configured). Otherwise a descriptive
    error message is returned.

    Parameters
    ----------
    query : str
        The search query.
    max_results : int, optional
        Maximum number of results to return, by default 5.
    topic : Literal["general", "news", "finance"], optional
        Topic category for Tavily search; ignored for Google search.
    include_raw_content : bool, optional
        Whether to include raw page contents in Tavily search results; ignored
        for Google search.

    Returns
    -------
    dict
        Either a search result structure or an error message.
    """
    # Prefer Google search if configured and available
    google_result = _google_custom_search(
       query,
       max_results=max_results,
       include_raw_content=include_raw_content,
       topic=topic,
    )
    if google_result is not None:
        return google_result
    # Fall back to Tavily search if a client is available
    if tavily_client is not None:
        try:
            return tavily_client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic,
            )
        except Exception as exc: # pragma: no cover - network/remote failures
            return {"error": str(exc), "query": query}
    # No search provider configured
    return {
        "error": "Web search disabled: set GOOGLE_API_KEY and GOOGLE_CSE_ID or TAVILY_API_KEY to enable search.",
        "query": query,
    }


# Agent prompts and sub‑agents

sub_research_prompt = """You are a dedicated researcher. Your job is to conduct research based on the users questions.

Conduct thorough research and then reply to the user with a detailed answer to their question

only your FINAL answer will be passed on to the user. They will have NO knowledge of anything except your final message, so your final report should be your final message!"""

research_sub_agent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions. Only give this researcher one topic at a time. Do not pass multiple sub questions to this researcher. Instead, you should break down a large topic into the necessary components, and then call multiple research agents in parallel, one for each sub question.",
    "prompt": sub_research_prompt,
    "tools": ["internet_search"],
}

sub_critique_prompt = """You are a dedicated editor. You are being tasked to critique a report.

You can find the report at `final_report.md`.

You can find the question/topic for this report at `question.txt`.

The user may ask for specific areas to critique the report in. Respond to the user with a detailed critique of the report. Things that could be improved.

You can use the search tool to search for information, if that will help you critique the report

Do not write to the `final_report.md` yourself.

Things to check:
- Check that each section is appropriately named
- Check that the report is written as you would find in an essay or a textbook - it should be text heavy, do not let it just be a list of bullet points!
- Check that the report is comprehensive. If any paragraphs or sections are short, or missing important details, point it out.
- Check that the article covers key areas of the industry, ensures overall understanding, and does not omit important parts.
- Check that the article deeply analyzes causes, impacts, and trends, providing valuable insights
- Check that the article closely follows the research topic and directly answers questions
- Check that the article has a clear structure, fluent language, and is easy to understand.
"""

critique_sub_agent = {
    "name": "critique-agent",
    "description": "Used to critique the final report. Give this agent some information about how you want it to critique the report.",
    "prompt": sub_critique_prompt,
}


# Prompt prefix to steer the agent to be an expert researcher
research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

The first thing you should do is to write the original user question to `question.txt` so you have a record of it.

Use the research-agent to conduct deep research. It will respond to your questions/topics with a detailed answer.

When you think you enough information to write a final report, write it to `final_report.md`

You can call the critique-agent to get a critique of the final report. After that (if needed) you can do more research and edit the `final_report.md`
You can do this however many times you want until are you satisfied with the result.

Only edit the file once at a time (if you call this tool in parallel, there may be conflicts).

Here are instructions for writing the final report:

<report_instructions>

CRITICAL: Make sure the answer is written in the same language as the human messages! If you make a todo plan - you should note in the plan what language the report should be in so you dont forget!
Note: the language the report should be in is the language the QUESTION is in, not the language/country that the question is ABOUT.

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections)
2. Includes specific facts and insights from the research
3. References relevant sources using [Title](URL) format
4. Provides a balanced, thorough analysis. Be as comprehensive as possible, and include all information that is relevant to the overall research question. People are using you for deep research and will expect detailed, comprehensive answers.
5. Includes a "Sources" section at the end with all referenced links

You can structure your report in a number of different ways. Here are some examples:

To answer a question that asks you to compare two things, you might structure your report like this:
1/ intro
2/ overview of topic A
3/ overview of topic B
4/ comparison between A and B
5/ conclusion

To answer a question that asks you to return a list of things, you might only need a single section which is the entire list.
1/ list of things or table of things
Or, you could choose to make each item in the list a separate section in the report. When asked for lists, you don't need an introduction or conclusion.
1/ item 1
2/ item 2
3/ item 3

To answer a question that asks you to summarize a topic, give a report, or give an overview, you might structure your report like this:
1/ overview of topic
2/ concept 1
3/ concept 2
4/ concept 3
5/ conclusion

If you think you can answer the question with a single section, you can do that too!
1/ answer

REMEMBER: Section is a VERY fluid and loose concept. You can structure your report however you think is best, including in ways that are not listed above!
Make sure that your sections are cohesive, and make sense for the reader.

For each section of the report, do the following:
- Use simple, clear language
- Use ## for section title (Markdown format) for each section of the report
- Do NOT ever refer to yourself as the writer of the report. This should be a professional report without any self-referential language. 
- Do not say what you are doing in the report. Just write the report without any commentary from yourself.
- Each section should be as long as necessary to deeply answer the question with the information you have gathered. It is expected that sections will be fairly long and verbose. You are writing a deep research report, and users will expect a thorough answer.
- Use bullet points to list out information when appropriate, but by default, write in paragraph form.

REMEMBER:
The brief and research may be in English, but you need to translate this information to the right language when writing the final answer.
Make sure the final answer report is in the SAME language as the human messages in the message history.

Format the report in clear markdown with proper structure and include source references where appropriate.

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Each source should be a separate line item in a list, so that in markdown it is rendered as a list.
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
- Citations are extremely important. Make sure to include these, and pay a lot of attention to getting these right. Users will often use these citations to look into more information.
</Citation Rules>
</report_instructions>

You have access to a few tools.

## `internet_search`

Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included.
"""

# Create the agent
# Optional: allow selecting a model via environment, e.g. DEEPAGENTS_MODEL="ollama:llama3.1:8b"
MODEL_ID = os.getenv("DEEPAGENTS_MODEL")
_model = init_chat_model(model=MODEL_ID) if MODEL_ID else None

agent = create_deep_agent(
    [internet_search],
    research_instructions,
    model=_model,  # if None, defaults to Anthropic; set DEEPAGENTS_MODEL to override
    subagents=[critique_sub_agent, research_sub_agent],
).with_config({"recursion_limit": 1000})
