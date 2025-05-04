import asyncio
from langchain.agents import initialize_agent, AgentType
from langchain.schema import AgentAction
from .bug_hunter import BugHunterAgent
from .vuln_seeker import VulnSeekerAgent
from .intent_guru import IntentGuruAgent
from .chat_central import ChatCentralAgent

class RouterAgent:
    def __init__(self):
        self.agents = {
            'bug': BugHunterAgent(),
            'vuln': VulnSeekerAgent(),
            'intent': IntentGuruAgent(),
            'chat': ChatCentralAgent(),
        }

    async def route(self, query_type: str, **kwargs):
        agent = self.agents.get(query_type)
        if not agent:
            raise ValueError(f"Unknown query type: {query_type}")
        return await agent.run(**kwargs)

# Example usage:
# router = RouterAgent()
# asyncio.run(router.route('bug', code='...'))
