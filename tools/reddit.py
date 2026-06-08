"""로컬 후기 — Reddit (개인용 무료 티어).

키 없으면 스킵. praw 미설치여도 그래프가 안 죽게 import 보호.
"""
import os


def search_reddit_tips(destination: str, topic: str = "things to do") -> dict:
    cid = os.getenv("REDDIT_CLIENT_ID")
    csecret = os.getenv("REDDIT_CLIENT_SECRET")
    if not (cid and csecret):
        return {"success": False, "skipped": True, "error": "Reddit 키 없음 (선택)"}

    try:
        import praw  # 미설치 시 ImportError → 아래 except 로
    except ImportError:
        return {"success": False, "error": "praw 미설치: pip install praw"}

    try:
        reddit = praw.Reddit(
            client_id=cid, client_secret=csecret,
            user_agent="travel-planner-demo by u/anon",
        )
        tips = []
        for s in reddit.subreddit("travel+JapanTravel").search(
            f"{destination} {topic}", limit=8, sort="relevance"
        ):
            tips.append({
                "title": s.title,
                "score": s.score,
                "url": f"https://reddit.com{s.permalink}",
            })
        return {"success": True, "tips": tips}
    except Exception as e:
        return {"success": False, "error": str(e)}
