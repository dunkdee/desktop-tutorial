import os, time, redis

r0 = redis.from_url(os.getenv("REDIS_URL","redis://redis:6379/1"))

def heartbeat():
    r0.set("jarvis:heartbeat", str(time.time()), ex=120)

if __name__ == "__main__":
    print("Jarvis orchestrator online.")
    while True:
        heartbeat()
        time.sleep(10)