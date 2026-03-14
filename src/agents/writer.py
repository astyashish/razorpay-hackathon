import asyncio
import json
import re
import os
from langchain_core.messages import HumanMessage

from src.utils import invoke_llm_resilient

AB_EMAIL_PROMPT = """Write 2 cold email variants for {name} ({title}) at {company}.

Company context:
- Description: {description}
- Headcount: {headcount}
- Funding stage: {funding_stage}
- Location: {location}

Use AT LEAST 3 of these specific signals (the more recent and specific, the better):
{signals_list}

Our product: NexusAI — an agentic sales intelligence platform that finds leads, researches them from 8+ sources, and sends personalized outreach automatically. We help GTM teams at B2B SaaS companies 10x their outreach without adding headcount.

VARIANT A — benefit-led opener: start with the core transformation/outcome
VARIANT B — signal-led opener: start with their single most urgent signal (the one that creates time pressure)

For EACH variant:
- subject_line: max 8 words, no emojis, must reference something specific
- body: exactly 3 paragraphs, max 90 words each
  Para 1: Hook (specific to them — reference a signal or data point)
  Para 2: Our solution (one clear sentence on what we do, one proof point)
  Para 3: Soft CTA (low-friction next step, mention 15 min)
- Do NOT use: "I hope this email finds you well", "touch base", "synergy", "leverage", "reach out"
- DO use: specific numbers, specific signals, their company name

Score each variant 1-10 on:
- specificity: does it use their actual data points?
- relevance: does it match their current situation and pain?
- cta_strength: is the next step clear, easy, and low-friction?

Return ONLY valid JSON (no markdown, no explanation):
{{
  "variant_a": "full email body with line breaks as \\n",
  "subject_a": "...",
  "score_a": {{"specificity": 1-10, "relevance": 1-10, "cta_strength": 1-10, "total": 1-10}},
  "variant_b": "full email body with line breaks as \\n",
  "subject_b": "...",
  "score_b": {{"specificity": 1-10, "relevance": 1-10, "cta_strength": 1-10, "total": 1-10}},
  "winner": "a" or "b",
  "reasoning": "one sentence explaining why the winner is better for this specific person right now"
}}"""

HTML_CARD_PROMPT = """Generate a self-contained HTML email intelligence card for {company}.

ABSOLUTE RULES (violations will break email clients):
1. ONLY inline styles — no <style> tags, no class attributes, no external CSS
2. No JavaScript whatsoever
3. Max-width: 480px
4. Background: #0f0f0e
5. All text must have explicit color property
6. All SVG must be inline (no src= references)
7. No external fonts (use font-family: Arial, Helvetica, sans-serif only)

SCORES (use these exact values):
- ICP Fit: {icp_fit}/10
- Intent: {intent}/10
- Budget: {budget}/10
- Timing: {timing}/10
- Reach: {reach}/10
- Signal Strength: {signal_strength}/10

SIGNALS TO DISPLAY:
1. {signal_1}
2. {signal_2}
3. {signal_3}

CARD STRUCTURE (in this exact order):
1. Header bar: dark (#1a1a18), company name in white 18px bold, "Intelligence Report" in #00e88f 10px monospace uppercase
2. SVG radar chart: 240x240px, 6 axes evenly spaced, scores as percentage of max (10), filled polygon in rgba(0,232,143,0.3) with stroke #00e88f 2px, axis labels in #888880 9px
3. Score bars section (4 rows): label (ICP Fit, Intent, Budget, Signal) in #888880 9px monospace | bar track 4px height #1a1a18 | filled bar gradient left-to-right #00e88f to #00b870 | percentage in #00e88f 10px
4. Signals section: title "KEY SIGNALS" in #555 8px monospace | 3 bullets, each with green circle prefix in #00e88f, text in #aaa8a2 11px
5. CTA button: full width, background #00e88f, text "Book 15-min Call" in #0a0a09 13px bold, padding 12px, border-radius 6px, href="https://calendly.com/nexusai"

Return ONLY the HTML string. No markdown code fences. No explanation. Start with <div and end with </div>."""

async def run_writer_agent(profile: dict, contact: dict, log_fn=None) -> dict:
    """Generate A/B emails with scoring and visual HTML card."""
    
    company_name = profile.get("company_name", "")
    signals = profile.get("signals", [])
    
    if log_fn:
        await log_fn(f"✍️ Writer: Generating A/B email variants for {contact['name']} at {company_name}...")
    
    # Format signals for prompt
    signals_list = "\n".join([
        f"- [{s.get('urgency','medium').upper()}] {s.get('signal', s) if isinstance(s, dict) else s}"
        for s in signals[:5]
    ]) if signals else "- Company is actively growing\n- B2B SaaS space\n- Needs GTM automation"
    
    email_prompt = AB_EMAIL_PROMPT.format(
        name=contact.get("name", "there"),
        title=contact.get("title", ""),
        company=company_name,
        description=profile.get("description", "")[:200],
        headcount=profile.get("headcount", "unknown"),
        funding_stage=profile.get("funding_stage", "unknown"),
        location=profile.get("hq_location", ""),
        signals_list=signals_list
    )
    
    # Generate email via LLM + build HTML card via template (no LLM needed)
    email_response, card_html = await asyncio.gather(
        asyncio.to_thread(lambda: invoke_llm_resilient([HumanMessage(content=email_prompt)], temperature=0.7)),
        asyncio.to_thread(lambda: _build_html_card_template(profile, contact))
    )
    card_response = card_html
    
    # Parse email JSON
    try:
        match = re.search(r'\{.*\}', email_response.content, re.DOTALL)
        email_result = json.loads(match.group()) if match else {}
    except:
        email_result = {
            "variant_a": "Fallback email A", "subject_a": "Quick question about your growth",
            "score_a": {"total": 6}, "variant_b": "Fallback email B",
            "subject_b": "Saw your recent news", "score_b": {"total": 7},
            "winner": "b", "reasoning": "Signal-led is more timely"
        }
    
    winner = email_result.get("winner", "b")
    best_email = email_result.get(f"variant_{winner}", "")
    best_subject = email_result.get(f"subject_{winner}", "")
    winner_score = email_result.get(f"score_{winner}", {})
    
    if log_fn:
        await log_fn(f"✅ Writer: Variant {winner.upper()} wins (score: {winner_score.get('total', 'N/A')}/10) — {email_result.get('reasoning', '')[:80]}")
        await log_fn(f"🎨 Writer: HTML card built via template ({len(card_response)} chars)")
    
    return {
        "variant_a": email_result.get("variant_a"),
        "variant_b": email_result.get("variant_b"),
        "subject_a": email_result.get("subject_a"),
        "subject_b": email_result.get("subject_b"),
        "score_a": email_result.get("score_a"),
        "score_b": email_result.get("score_b"),
        "winner": winner,
        "winner_reasoning": email_result.get("reasoning", ""),
        "best_email": best_email,
        "best_subject": best_subject,
        "html_card": card_response
    }

async def generate_html_card(profile: dict, contact: dict, log_fn=None) -> str:
    """Generate self-contained visual HTML pitch card."""
    scores = profile.get("scores", {})
    signals = profile.get("signals", [])
    
    def get_signal_text(s):
        return s.get("signal", str(s)) if isinstance(s, dict) else str(s)
    
    card_prompt = HTML_CARD_PROMPT.format(
        company=profile.get("company_name", "Company"),
        icp_fit=scores.get("icp_fit", 7),
        intent=scores.get("intent", 8),
        budget=scores.get("budget", 6),
        timing=scores.get("timing", 9),
        reach=scores.get("reach", 7),
        signal_strength=scores.get("signal_strength", 8),
        signal_1=get_signal_text(signals[0]) if len(signals) > 0 else "Active hiring detected",
        signal_2=get_signal_text(signals[1]) if len(signals) > 1 else "Recent funding round",
        signal_3=get_signal_text(signals[2]) if len(signals) > 2 else "ProductHunt launch"
    )
    
    response = await asyncio.to_thread(lambda: invoke_llm_resilient([HumanMessage(content=card_prompt)], temperature=0.1))
    html = response.content.strip()
    
    # Clean up any accidental markdown fences
    html = re.sub(r'^```html?\s*', '', html)
    html = re.sub(r'\s*```$', '', html)
    
    if log_fn:
        await log_fn(f"🎨 Writer: Visual HTML card generated ({len(html)} chars, inline styles only)")
    
    return html


def _build_html_card_template(profile: dict, contact: dict) -> str:
    """Build HTML intelligence card using a fast Python template (no LLM call)."""
    scores = profile.get("scores", {})
    signals = profile.get("signals", [])
    company = profile.get("company_name", "Company")

    def get_signal_text(s):
        return s.get("signal", str(s)) if isinstance(s, dict) else str(s)

    icp_fit = scores.get("icp_fit", 7)
    intent = scores.get("intent", 8)
    budget = scores.get("budget", 6)
    timing = scores.get("timing", 9)
    reach = scores.get("reach", 7)
    signal_strength = scores.get("signal_strength", 8)

    signal_1 = get_signal_text(signals[0]) if len(signals) > 0 else "Active hiring detected"
    signal_2 = get_signal_text(signals[1]) if len(signals) > 1 else "Recent funding round"
    signal_3 = get_signal_text(signals[2]) if len(signals) > 2 else "ProductHunt launch"

    def bar(label, value):
        pct = int((value / 10) * 100)
        return f'''<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
  <span style="color:#888880;font-size:9px;font-family:monospace;width:80px;text-transform:uppercase;">{label}</span>
  <div style="flex:1;height:4px;background:#1a1a18;border-radius:2px;overflow:hidden;">
    <div style="width:{pct}%;height:100%;border-radius:2px;background:linear-gradient(90deg,#00e88f,#00b870);"></div>
  </div>
  <span style="color:#00e88f;font-size:10px;font-family:monospace;width:24px;text-align:right;">{value}</span>
</div>'''

    def signal_row(text):
        return f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:4px;"><span style="color:#00e88f;flex-shrink:0;">&#9679;</span><span style="color:#aaa8a2;font-size:11px;font-family:Arial,sans-serif;">{text}</span></div>'

    return f'''<div style="max-width:480px;background:#0f0f0e;border-radius:12px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;">
  <div style="background:#1a1a18;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div style="color:#fff;font-size:18px;font-weight:bold;">{company}</div>
      <div style="color:#00e88f;font-size:10px;font-family:monospace;text-transform:uppercase;letter-spacing:2px;">Intelligence Report</div>
    </div>
    <div style="color:#00e88f;font-size:28px;font-weight:bold;font-family:monospace;">{icp_fit}<span style="font-size:12px;color:#888880;">/10</span></div>
  </div>
  <div style="padding:20px;">
    {bar("ICP Fit", icp_fit)}
    {bar("Intent", intent)}
    {bar("Budget", budget)}
    {bar("Timing", timing)}
    {bar("Reach", reach)}
    {bar("Signal", signal_strength)}
  </div>
  <div style="padding:0 20px 16px;">
    <div style="color:#555;font-size:8px;font-family:monospace;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">Key Signals</div>
    {signal_row(signal_1)}
    {signal_row(signal_2)}
    {signal_row(signal_3)}
  </div>
  <div style="padding:0 20px 20px;">
    <a href="https://calendly.com/nexusai" style="display:block;background:#00e88f;color:#0a0a09;text-align:center;padding:12px;border-radius:6px;font-size:13px;font-weight:bold;text-decoration:none;">Book 15-min Call</a>
  </div>
</div>'''
