import asyncio
import json
import logging
import os
import re
from collections import Counter
from typing import Protocol, Collection

import tiktoken
from openai import AsyncOpenAI
from typing_extensions import override

from src.config import ChatGptClientConfig, TextProcessorConfig
from src.exception.data_exception import JsonNotFountError, WrongJsonStructureError
from src.gui.state_manager import global_state_manager

logger = logging.getLogger("app_logger")


class LLMClientProtocol(Protocol):

    async def get_response(self, prompt: str) -> Collection[str]:
        ...

    def count_tokens(self, text: str) -> int:
        ...

    def get_available_token_count(self) -> int:
        ...


class JsonAdapterProtocol(Protocol):

    def map_json(self, data: dict) -> dict:
        ...


class DefaultJsonAdapter(JsonAdapterProtocol):

    @override
    def map_json(self, choice: dict) -> dict:
        try:
            result = {'objects': {}, 'object_properties': {}, 'data_properties': {}}
            if 'objects' in choice and choice['objects']:
                DefaultJsonAdapter.__map_objects(choice['objects'], result['objects'])
                if 'object_properties' in choice and choice['object_properties']:
                    DefaultJsonAdapter.__map_object_properties(choice['object_properties'], result['object_properties'])
                if 'data_properties' in choice and choice['data_properties']:
                    DefaultJsonAdapter.__map_data_properties(choice['data_properties'], result['data_properties'])
            return result

        except Exception:
            raise WrongJsonStructureError

    @staticmethod
    def __map_objects(objects: dict, result_objects: dict):
        for obj in objects:
            if obj[0] not in result_objects:
                result_objects[obj[0]] = {(obj[1], tuple(tuple(label) for label in obj[2]))}
            else:
                result_objects[obj[0]].add((obj[1], tuple(tuple(label) for label in obj[2])))

    @staticmethod
    def __map_object_properties(object_properties: dict, result_object_properties: dict):
        for obj_prop in object_properties:
            subject_name, object_name = obj_prop[1][0], obj_prop[1][1]
            if obj_prop[0] not in result_object_properties:
                result_object_properties[obj_prop[0]] = {(subject_name, object_name)}
            else:
                result_object_properties[obj_prop[0]].add((subject_name, object_name))

    @staticmethod
    def __map_data_properties(data_properties: dict, result_data_properties: dict):
        for data_prop in data_properties:
            object_name, value = data_prop[1]
            if data_prop[0] not in result_data_properties:
                result_data_properties[data_prop[0]] = {(object_name, value)}
            else:
                result_data_properties[data_prop[0]].add((object_name, value))


class ChatGptClient(LLMClientProtocol):
    def __init__(self, config: ChatGptClientConfig, prompt_instruction: str):
        self.__prompt_instruction = prompt_instruction
        self.__num_responses = config.num_responses
        self.__system_message = config.system_message
        self.__model = config.model
        self.__temperature = config.temperature
        self.__encoding = tiktoken.encoding_for_model(config.model)
        self.__available_token_count = config.model_tokens_limitation - self.count_tokens(
            self.__prompt_instruction) - self.count_tokens(self.__system_message) - 5
        self.__client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    @override
    async def get_response(self, text: str) -> Collection[str]:
        full_prompt = f"{self.__prompt_instruction}\n{text}"
        global_state_manager.trigger_callback('update_ChatGPT_request_tab', full_prompt)
        response = await self.__client.chat.completions.create(
            model=self.__model,
            messages=[
                {"role": "system", "content": self.__system_message},
                {"role": "user", "content": full_prompt}
            ],
            temperature=self.__temperature,
            n=self.__num_responses
        )
        return [choice.message.content for choice in response.choices]

    @override
    def count_tokens(self, text: str) -> int:
        return len(self.__encoding.encode(text))

    @override
    def get_available_token_count(self) -> int:
        return self.__available_token_count


class TextProcessor:
    def __init__(self, config: TextProcessorConfig, llm_client: LLMClientProtocol, json_adapter: JsonAdapterProtocol):
        self.__threshold = config.threshold
        self.__overlap_sentences = config.overlap_sentences
        self.__separators = config.separators
        self.__semaphore = asyncio.Semaphore(config.text_processor_semaphore_size)

        self.__llm_client = llm_client
        self.__json_adapter = json_adapter
        self.__tokens_limitation = llm_client.get_available_token_count()

    async def process_text(self, text: str):
        chunks = self.__split_text_into_chunks(text)
        tasks = [asyncio.create_task(self.__process_chunk(chunk)) for chunk in chunks]
        return tasks

    async def __process_chunk(self, chunk: str):
        async with self.__semaphore:
            response = await self.__llm_client.get_response(chunk)
        counter_dict = {'objects': Counter(), 'object_properties': Counter(), 'data_properties': Counter()}
        for choice in response:
            try:
                json_choice = TextProcessor.__extract_json(choice)
                self.__add_choice_to_counter(self.__json_adapter.map_json(json_choice), counter_dict)
            except json.JSONDecodeError as e:
                logger.error("", exc_info=True)
                global_state_manager.trigger_callback('update_errors_tab',
                                                      "Wrong Chat GPT response structure:\n" + choice)
                continue
            except WrongJsonStructureError as e:
                logger.error("", exc_info=True)
                global_state_manager.trigger_callback('update_errors_tab',
                                                      "Wrong JSON structure in Chat GPT response:\n" + json_choice)
                continue
        if counter_dict['objects']:
            return self.__make_consistent(counter_dict)

    @staticmethod
    def __extract_json(choice: str):
        json_pattern = re.compile(r'(\{.*\})', re.DOTALL)
        match = json_pattern.search(choice)

        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        else:
            raise JsonNotFountError(choice)

    def __make_consistent(self, counters_dict: dict):
        result = {'objects': {}, 'object_properties': {}, 'data_properties': {}}
        for entity_type, classes in counters_dict.items():
            for class_name, entities in classes.items():
                for entity, count in entities.items():
                    if count >= self.__threshold:
                        if class_name not in result[entity_type]:
                            result[entity_type][class_name] = {entity}
                        result[entity_type][class_name].add(entity)
        global_state_manager.trigger_callback('update_ChatGPT_response_tab', result)
        return result

    @staticmethod
    def __add_choice_to_counter(choice, counters_dict: dict):
        for entity_type, classes in choice.items():
            for class_name, entities in classes.items():
                if class_name not in counters_dict[entity_type]:
                    counters_dict[entity_type][class_name] = Counter(entities)
                else:
                    counters_dict[entity_type][class_name].update(entities)

    def __is_within_limit(self, text: str):
        token_count = self.__llm_client.count_tokens(text)
        return token_count <= self.__tokens_limitation

    def __split_into_sentences(self, text):
        pattern = '|'.join(map(re.escape, self.__separators))
        sentences = re.split(f'({pattern})', text)
        return [''.join(pair) for pair in zip(sentences[::2], sentences[1::2])]

    def __split_text_into_chunks(self, text: str):
        if self.__is_within_limit(text):
            return [text]

        sentences = self.__split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_token_count = 0

        for sentence in sentences:
            sentence_token_count = self.__llm_client.count_tokens(sentence)
            if current_token_count + sentence_token_count > self.__tokens_limitation:
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                # todo make else statement to cover big sentence case
                current_chunk = current_chunk[-self.__overlap_sentences:] if self.__overlap_sentences else []
                current_token_count = self.__llm_client.count_tokens(''.join(current_chunk))

            current_chunk.append(sentence)
            current_token_count += sentence_token_count

        if current_chunk:
            chunks.append(''.join(current_chunk))
        return chunks
