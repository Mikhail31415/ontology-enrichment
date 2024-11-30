import asyncio
import logging

from src.config import ChatGptClientConfig, TextProcessorConfig, get_yaml_configs
from src.gui.state_manager import global_state_manager
from src.repository.kb_repository import KBRepository
from src.repository.ontology_owlready2_repository import OntologyOwlready2Repository
from src.text_processor import ChatGptClient, TextProcessor, DefaultJsonAdapter, LLMClientProtocol
from src.text_producer import WebScraper, FromWebScraperSource, FromNLFileSource, TextSource

logger = logging.getLogger("app_logger")


class AppLogic:
    __kb_repository: KBRepository
    __llm_client: LLMClientProtocol
    __text_source: TextSource

    def __init__(self, place_generator, prompt, onto, save_ontology_path, mode):
        configs = get_yaml_configs()
        logger.info(configs)
        self.__onto = onto
        self.__place_generator = place_generator
        self.__prompt = prompt
        self.__kb_repository = OntologyOwlready2Repository(self.__onto, save_ontology_path)
        self.__llm_client = ChatGptClient(ChatGptClientConfig.from_yaml(configs['openai']), prompt)
        self.__text_processor = TextProcessor(TextProcessorConfig.from_yaml(configs['text_processor']),
                                              self.__llm_client,
                                              DefaultJsonAdapter())
        if mode == 'nl_file':
            self.__text_source = FromNLFileSource()
        else:
            self.__text_source = FromWebScraperSource(WebScraper)

    async def __worker(self):
        async for place in self.__place_generator:
            if not global_state_manager.get_state("processing"):
                break
            try:
                text = await self.__text_source.get_text(place)
                tasks = await self.__text_processor.process_text(text)

                for task in asyncio.as_completed(tasks):
                    processed_chunk = await task
                    self.__kb_repository.add_individuals(processed_chunk)

                global_state_manager.trigger_callback("update_url_count", 1)

            except Exception as e:
                logger.error("Unexpected error during processing " + place, exc_info=True)
                global_state_manager.trigger_callback("update_errors_tab",
                                                      "Unexpected error during processing " + place)
                continue

    async def run(self, pool_size=1):
        tasks = [asyncio.create_task(self.__worker()) for _ in range(pool_size)]
        await asyncio.gather(*tasks)
        global_state_manager.trigger_callback("switch_button_to_start", None)
