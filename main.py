from fastapi import FastAPI
from api.routes import router
import uvicorn

app = FastAPI()

app.include_router(router)

# 这个条件语句确保在本地运行时才执行uvicorn.run()
# Vercel会自动处理应用的运行，不需要这部分代码
if __name__ == "__main__":
    uvicorn.run(app)

# 为Vercel部署添加这一行
# Vercel需要一个名为"app"的变量作为入口点
app = app
