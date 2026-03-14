from ddgs import DDGS

def google_search(query):
    """
    Performs a web search using DuckDuckGo (free, no API key required).
    Returns results in the same format as before: list of {title, link, snippet}.
    """
    with DDGS() as ddgs:
        raw = list(ddgs.text(query, max_results=10))
    return [
        {"title": r.get("title", ""), "link": r.get("href", ""), "snippet": r.get("body", "")}
        for r in raw
    ]

def get_recent_news(company: str) -> str:
    """
    Fetches recent news about a company using DuckDuckGo News (free, no API key).
    """
    with DDGS() as ddgs:
        raw = list(ddgs.news(company, max_results=20, timelimit="y"))

    if not raw:
        return "No recent news found."

    raw.reverse()
    news_string = ""
    for item in raw:
        title = item.get("title", "")
        snippet = item.get("body", "")
        date = item.get("date", "")
        link = item.get("url", "")
        news_string += f"Title: {title}\nSnippet: {snippet}\nDate: {date}\nURL: {link}\n\n"

    return news_string
