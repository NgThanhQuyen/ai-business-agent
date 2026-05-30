import logging

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit, create_sql_agent
from langchain_groq import ChatGroq

from core.config import settings
from database.db import engine


logger = logging.getLogger(__name__)


def ask_database(user_question: str) -> str:
    """Trả lời câu hỏi ngôn ngữ tự nhiên bằng cách truy vấn cơ sở dữ liệu SQL."""
    try:
        db = SQLDatabase(engine)

        llm = ChatGroq(
            model_name="llama-3.3-70b-versatile",
            temperature=0,
            api_key=settings.GROQ_API_KEY,
        )

        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        agent_executor = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            agent_type="tool-calling",
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
        )

        response = agent_executor.invoke({"input": user_question})
        return str(response.get("output", ""))
    except Exception:
        logger.exception("SQL agent failed")
        return (
            "Xin loi, toi gap su co khi truy van co so du lieu. "
            "Vui long thu lai voi cau hoi khac."
        )
