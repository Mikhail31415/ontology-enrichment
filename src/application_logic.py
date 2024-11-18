import asyncio
import logging

from src.config import ChatGptClientConfig, TextProcessorConfig, get_yaml_configs
from src.gui.state_manager import global_state_manager
from src.repository.kb_repository import KBRepository
from src.repository.ontology_owlready2_repository import OntologyOwlready2Repository
from src.text_processor import ChatGptClient, TextProcessor, DefaultJsonAdapter, LLMClientProtocol
from src.text_producer import WebScraper, FromWebScraperSource, FromNLFileSource, TextSource


class AppLogic:
    kb_repository: KBRepository
    llm_client: LLMClientProtocol
    text_source: TextSource

    def __init__(self, place_generator, prompt, onto, save_ontology_path, mode):
        configs = get_yaml_configs()
        self.onto = onto
        self.place_generator = place_generator
        self.prompt = prompt
        self.kb_repository = OntologyOwlready2Repository(self.onto, save_ontology_path)
        self.llm_client = ChatGptClient(ChatGptClientConfig.from_yaml(configs['openai']), prompt)
        self.text_processor = TextProcessor(TextProcessorConfig.from_yaml(configs['text_processor']), self.llm_client, DefaultJsonAdapter())
        if mode == 'nl_file':
            self.text_source = FromNLFileSource()
        else:
            self.text_source = FromWebScraperSource(WebScraper)


    async def worker(self):
        async for place in self.place_generator:
            if not global_state_manager.get_state("processing"):
                break
            try:
                text = await self.text_source.get_text(place)
                tasks = await self.text_processor.process_text(text)

                for task in asyncio.as_completed(tasks):
                    processed_chunk = await task
                    self.kb_repository.add_individuals(processed_chunk)

                global_state_manager.trigger_callback("update_url_count", 1)

            except Exception as e:
                logging.error("Unexpected error during processing " + place, exc_info=True)
                global_state_manager.trigger_callback("update_errors_tab", "Unexpected error during processing " + place)
                continue

    async def run(self, pool_size=1):
        tasks = [asyncio.create_task(self.worker()) for _ in range(pool_size)]
        await asyncio.gather(*tasks)

