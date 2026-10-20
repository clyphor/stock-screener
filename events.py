"""Company-event taxonomy: classify each headline into events with a typical price impact.

Impacts are rough priors (-1..1) for how such news usually moves a stock in the following days.
Claude (if ANTHROPIC_API_KEY is set) uses the same event list, and can judge context the
rules miss; without a key these regex rules are used.
"""
import re

# key: (label, impact, regex)  — first matching rules all count; strongest impact wins ties
EVENTS = {
    "takeover_target": ("Takeover bid received", 0.7,
        r"\b(takeover (offer|bid|approach|proposal)|buyout (offer|bid)|to be (acquired|bought)|agrees? to be (acquired|bought)"
        r"|receives? .{0,30}(offer|bid|proposal)|rebuff\w* .{0,30}(offer|bid|approach)|rejects? .{0,30}(offer|bid|proposal))\b"),
    "acquirer": ("Making an acquisition", -0.05,
        r"\b(to acquire|acquires|acquisition of|agrees? to buy|snaps up|bid for|offer for|merger with)\b"),
    "contract_win": ("Contract / order win", 0.6,
        r"\b(wins?|won|awarded|secures?|lands?|clinch\w*|signs?)\b.{0,40}\b(contract|order|tender|deal|offtake)\b"
        r"|\bcontract (win|award)\b|\b(government|defen[cs]e|pentagon|army|navy) (contract|order)\b"),
    "partnership": ("Partnership / agreement", 0.35,
        r"\b(partner(s|ship|ing)? with|collaborat\w+ with|alliance|joint venture|teams? up|MoU|memorandum of understanding"
        r"|strategic (agreement|deal)|supply agreement|licensing (deal|agreement)|signs? .{0,20}agreement)\b"),
    "ceo_exit": ("CEO / leadership exit", -0.35,
        r"\b(CEO|chief executive|chair(man|woman)?|CFO|managing director|founder)\b.{0,50}"
        r"\b(resign\w*|steps? down|stepping down|depart\w*|quits?|ousted|fired|sacked|axed|exit\w*|to leave)\b"),
    "ceo_new": ("New CEO / leadership", 0.1,
        r"\b(appoints?|names?|hires?|picks?|taps?)\b.{0,40}\b(CEO|chief executive|CFO|chair\w*|managing director)\b"
        r"|\bnew (CEO|chief executive|boss)\b"),
    "scandal": ("Scandal / probe / fraud", -0.8,
        r"\b(fraud|scandal|probe\w*|investigat\w+|subpoena\w*|whistle-?blower|misconduct|brib\w+|corruption"
        r"|accounting (irregularit\w+|error|issue)|short[- ]?seller|short report|SEC charges?|ASIC (sues|action|probe)"
        r"|DOJ|raid\w*|money laundering|cover-?up)\b"),
    "lawsuit": ("Lawsuit / legal action", -0.4,
        r"\b(lawsuit|sued|sues|litigation|legal action|class action|court (rules|ruling) against|verdict against|fined|penalt\w+|settlement)\b"),
    "approval": ("Regulatory approval", 0.6,
        r"\b(FDA|TGA|EMA|FTC|ACCC|FIRB|regulators?)\b.{0,40}\b(approv\w+|clear\w*|green light|authori[sz]\w+|nod)\b"
        r"|\b(wins?|receives?|gets?) .{0,20}approval\b"),
    "rejection": ("Regulatory rejection / block", -0.6,
        r"\b(FDA|TGA|EMA|FTC|ACCC|FIRB|regulators?)\b.{0,40}\b(reject\w*|block\w*|halt\w*|deny|denies|denied|oppos\w+|sues)\b"
        r"|\bcomplete response letter\b|\bclinical hold\b"),
    "trial_success": ("Trial success", 0.6, r"\b(trial|study)\b.{0,40}\b(succe\w+|positive|met .{0,10}endpoint|meets? .{0,10}endpoint)\b"),
    "trial_fail": ("Trial failure", -0.7, r"\b(trial|study)\b.{0,40}\b(fail\w*|miss\w*|halted|discontinu\w+)\b"),
    "guidance_up": ("Raised guidance", 0.6,
        r"\b(raises?|lifts?|boosts?|ups|upgrades?|hikes?) .{0,20}(guidance|forecast|outlook)\b"),
    "guidance_down": ("Cut guidance / profit warning", -0.7,
        r"\b(cuts?|lowers?|slashes?|downgrades?|withdraws?|trims?) .{0,20}(guidance|forecast|outlook)\b|\bprofit warning\b"),
    "beat": ("Results beat", 0.5,
        r"\b(beats?|tops?|exceeds?|surpass\w*|smash\w*) .{0,25}(estimates|expectations|forecasts|consensus)\b"
        r"|\brecord (profit|revenue|earnings|sales|quarter)\b"),
    "miss": ("Results miss", -0.5,
        r"\bmiss(es|ed)? .{0,25}(estimates|expectations|forecasts|consensus)\b"
        r"|\b(profit|earnings|revenue|sales) (falls?|drops?|slumps?|plunges?|tumbles?|sinks?)\b|\bloss widens\b"),
    "analyst_up": ("Analyst upgrade / target raised", 0.35,
        r"\bupgrade[sd]? .{0,20}(to (buy|outperform|overweight))|\b(raises?|lifts?|boosts?|hikes?) .{0,15}(price )?target\b"
        r"|\binitiat\w+ .{0,25}(buy|outperform|overweight)\b|\bupgraded\b"),
    "analyst_down": ("Analyst downgrade / target cut", -0.35,
        r"\bdowngrade[sd]?\b|\b(cuts?|lowers?|trims?|slashes?) .{0,15}(price )?target\b|\b(underperform|underweight|sell rating)\b"),
    "buyback": ("Share buyback", 0.4, r"\b(buy-?back|share repurchase|repurchase program)\b"),
    "dividend_up": ("Dividend raised / special", 0.3, r"\b(raises?|increases?|hikes?|lifts?|boosts?) .{0,15}dividend\b|\bspecial dividend\b"),
    "dividend_cut": ("Dividend cut", -0.5, r"\b(cuts?|suspends?|slashes?|scraps?|axes?) .{0,15}dividend\b"),
    "capital_raise": ("Capital raising (dilution)", -0.4,
        r"\b(capital raising|placement|share purchase plan|equity raise|entitlement offer|rights issue|stock offering"
        r"|secondary offering|raises? (A|US)?\$ ?[\d.]+ ?(m|mn|million|bn|billion))\b"),
    "debt": ("Credit downgrade / debt stress", -0.5,
        r"\b(credit rating|rating) (cut|downgrade\w*)|\b(Moody's|S&P|Fitch) (cuts|downgrades)\b|\bjunk\b|\brefinanc\w+ (risk|concern)"),
    "bankruptcy": ("Bankruptcy / administration", -1.0,
        # not "Trump administration" or crypto "liquidations" (forced selling of leveraged bets)
        r"\b(bankrupt\w*|chapter 11|(enters?|entered|placed|goes|went|into|in) (voluntary )?administration"
        r"|administrators? (appointed|called)|receivership|insolven\w+|(into|enters?|entered|voluntary) liquidation"
        r"|liquidators?|defaults? on)\b"),
    "layoffs": ("Layoffs / restructuring", -0.1, r"\b(layoffs?|job cuts|cuts? [\d,]+ jobs|restructur\w+|cost[- ]cutting)\b"),
    "recall": ("Recall / outage / hack", -0.5,
        r"\b(recall\w*|outage|cyber-?attack|data breach|hack(ed|ers)?|ransomware|grounded|safety (issue|concern|probe))\b"),
    "strike": ("Strike / industrial action", -0.3, r"\b(strike action|workers? (strike|walk out)|industrial action|union strike)\b"),
    "launch": ("Product launch", 0.25, r"\b(launch\w*|unveil\w*|rolls? out|debuts?|introduces?)\b"),
    "discovery": ("Discovery / drilling success", 0.6,
        r"\b(discover\w*|high[- ]grade|drilling results|intercepts?|resource (upgrade|increase)|maiden (resource|reserve)"
        r"|reserve (upgrade|increase)|new (deposit|find|oil field|gas field))\b"),
    "production": ("Record production", 0.4, r"\brecord (production|output|shipments|deliveries)\b|\bproduction (beats|rises|jumps)\b"),
    "production_down": ("Production problem", -0.45,
        r"\b(production|output|shipments|deliveries) (cut|falls?|drops?|halted|suspended|disrupted)\b|\b(mine|plant|refinery) (closure|shut\w*|fire|accident)\b"),
    "index_add": ("Added to index", 0.3, r"\b(added to|join\w*|inclusion in|enter\w*) .{0,20}(S&P ?500|ASX ?(50|100|200)|Nasdaq-?100|index)\b"),
    "index_drop": ("Removed from index", -0.3, r"\b(removed from|drop\w* from|exit\w* from|delet\w+ from) .{0,20}(S&P ?500|ASX ?(50|100|200)|index)\b"),
    "insider_buy": ("Insider buying", 0.3, r"\b(directors?|insiders?|CEO|chair\w*) (buys?|bought|purchas\w+|snaps? up)\b"),
    "insider_sell": ("Insider selling", -0.2, r"\b(directors?|insiders?|CEO|chair\w*|founder) (sells?|sold|offload\w*|dump\w*|unload\w*)\b"),
    "gov_support": ("Government backing / funding", 0.45,
        r"\b(government|federal|state) .{0,20}(funding|grant|loan|stake|backing|support|subsid\w+)\b|\b(CHIPS Act|Export Finance)\b"),
    "trading_halt": ("Trading halt (news pending)", 0.0, r"\btrading halt\b"),
}
_RX = {k: re.compile(v[2], re.I) for k, v in EVENTS.items()}
LABEL = {k: v[0] for k, v in EVENTS.items()}
IMPACT = {k: v[1] for k, v in EVENTS.items()}
GOOD = {LABEL[k] for k, v in IMPACT.items() if v >= 0.3}
BAD = {LABEL[k] for k, v in IMPACT.items() if v <= -0.3}


def classify(title):
    """Return list of event keys found in a headline (most specific first)."""
    found = [k for k, rx in _RX.items() if rx.search(title)]
    # Avoid double counting: a takeover target is not also 'acquirer'; upgrades of guidance aren't analyst upgrades
    if "takeover_target" in found and "acquirer" in found:
        found.remove("acquirer")
    if ("guidance_up" in found or "guidance_down" in found):
        found = [k for k in found if k not in ("analyst_up", "analyst_down")]
    if "scandal" in found and "lawsuit" in found:
        found.remove("lawsuit")
    if "debt" in found and "analyst_down" in found:
        found.remove("analyst_down")
    if "launch" in found and any(IMPACT[k] <= -0.3 for k in found):  # "launches probe" is not a product
        found.remove("launch")
    return found


def event_score(keys):
    """Combine event impacts: the strongest drives it, others add a little."""
    vals = sorted((IMPACT[k] for k in keys if IMPACT[k] != 0), key=abs, reverse=True)
    if not vals:
        return None
    return max(-1.0, min(1.0, vals[0] + 0.25 * sum(vals[1:])))
