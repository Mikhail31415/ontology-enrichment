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
                DefaultJsonAdapter.map_objects(choice['objects'], result['objects'])
                if 'object_properties' in choice and choice['object_properties']:
                    DefaultJsonAdapter.map_object_properties(choice['object_properties'], result['object_properties'])
                if 'data_properties' in choice and choice['data_properties']:
                    DefaultJsonAdapter.map_data_properties(choice['data_properties'], result['data_properties'])
            return result

        except Exception:
            raise WrongJsonStructureError

    @staticmethod
    def map_objects(objects: dict, result_objects: dict):
        for obj in objects:
            if obj[0] not in result_objects:
                result_objects[obj[0]] = {(obj[1], tuple(tuple(label) for label in obj[2]))}
            else:
                result_objects[obj[0]].add((obj[1], tuple(tuple(label) for label in obj[2])))

    @staticmethod
    def map_object_properties(object_properties: dict, result_object_properties: dict):
        for obj_prop in object_properties:
            subject_name, object_name = obj_prop[1][0], obj_prop[1][1]
            if obj_prop[0] not in result_object_properties:
                result_object_properties[obj_prop[0]] = {(subject_name, object_name)}
            else:
                result_object_properties[obj_prop[0]].add((subject_name, object_name))

    @staticmethod
    def map_data_properties(data_properties: dict, result_data_properties: dict):
        for data_prop in data_properties:
            object_name, value = data_prop[1]
            if data_prop[0] not in result_data_properties:
                result_data_properties[data_prop[0]] = {(object_name, value)}
            else:
                result_data_properties[data_prop[0]].add((object_name, value))


class ChatGptClient(LLMClientProtocol):
    def __init__(self, config: ChatGptClientConfig, prompt_instruction: str):
        self.prompt_instruction = prompt_instruction
        self.num_responses = config.num_responses
        self.system_message = config.system_message
        self.model = config.model
        self.temperature = config.temperature
        self.encoding = tiktoken.encoding_for_model(config.model)
        self.available_token_count = config.model_tokens_limitation - self.count_tokens(self.prompt_instruction) - self.count_tokens(self.system_message) - 5
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    @override
    async def get_response(self, text: str) -> Collection[str]:
        full_prompt = f"{self.prompt_instruction}\n{text}"
        global_state_manager.trigger_callback('update_ChatGPT_request_tab', full_prompt)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": full_prompt}
            ],
            temperature=self.temperature,
            n=self.num_responses
        )
        return [choice.message.content for choice in response.choices]

    @override
    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    @override
    def get_available_token_count(self) -> int:
        return self.available_token_count



class TextProcessor:
    def __init__(self, config: TextProcessorConfig, llm_client: LLMClientProtocol, json_adapter: JsonAdapterProtocol):
        self.threshold = config.threshold
        self.overlap_sentences = config.overlap_sentences
        self.separators = config.separators
        self.semaphore = asyncio.Semaphore(config.text_processor_semaphore_size)

        self.llm_client = llm_client
        self.json_adapter = json_adapter
        self.tokens_limitation = llm_client.get_available_token_count()
        self.logger = logging.getLogger("app_logger")

    async def process_text(self, text: str):
        chunks = self.split_text_into_chunks(text)
        tasks = [asyncio.create_task(self.process_chunk(chunk)) for chunk in chunks]
        return tasks

    async def process_chunk(self, chunk):
        async with self.semaphore:
            response = await self.llm_client.get_response(chunk)
        counter_dict = {'objects': Counter(), 'object_properties': Counter(), 'data_properties': Counter()}
        for choice in response:
            try:
                json_choice = TextProcessor.extract_json(choice)
                self.add_choice_to_counter(self.json_adapter.map_json(json_choice), counter_dict)
            except json.JSONDecodeError as e:
                self.logger.error("", exc_info=True)
                global_state_manager.trigger_callback('update_errors_tab',
                                                      "Wrong Chat GPT response structure:\n" + choice)
                continue
            except WrongJsonStructureError as e:
                self.logger.error("", exc_info=True)
                global_state_manager.trigger_callback('update_errors_tab',
                                                      "Wrong JSON structure in Chat GPT response:\n" + json_choice)
                continue
        if counter_dict['objects']:
            return self.make_consistent(counter_dict)

    @staticmethod
    def extract_json(choice):
        json_pattern = re.compile(r'(\{.*\})', re.DOTALL)
        match = json_pattern.search(choice)

        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        else:
            raise JsonNotFountError(choice)

    def make_consistent(self, counters_dict):
        result = {'objects': {}, 'object_properties': {}, 'data_properties': {}}
        for entity_type, classes in counters_dict.items():
            for class_name, entities in classes.items():
                for entity, count in entities.items():
                    if count >= self.threshold:
                        if class_name not in result[entity_type]:
                            result[entity_type][class_name] = {entity}
                        result[entity_type][class_name].add(entity)
        global_state_manager.trigger_callback('update_ChatGPT_response_tab', result)
        print(result)
        return result

    @staticmethod
    def add_choice_to_counter(choice, counters_dict: dict):
        for entity_type, classes in choice.items():
            for class_name, entities in classes.items():
                if class_name not in counters_dict[entity_type]:
                    counters_dict[entity_type][class_name] = Counter(entities)
                else:
                    counters_dict[entity_type][class_name].update(entities)

    def is_within_limit(self, text):
        token_count = self.llm_client.count_tokens(text)
        return token_count <= self.tokens_limitation

    def split_into_sentences(self, text):
        pattern = '|'.join(map(re.escape, self.separators))
        sentences = re.split(f'({pattern})', text)
        return [''.join(pair) for pair in zip(sentences[::2], sentences[1::2])]

    def split_text_into_chunks(self, text):
        if self.is_within_limit(text):
            return [text]

        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_token_count = 0

        for sentence in sentences:
            sentence_token_count = self.llm_client.count_tokens(sentence)
            if current_token_count + sentence_token_count > self.tokens_limitation:
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                # todo make else statement to cover big sentence case
                current_chunk = current_chunk[-self.overlap_sentences:] if self.overlap_sentences else []
                current_token_count = self.llm_client.count_tokens(''.join(current_chunk))

            current_chunk.append(sentence)
            current_token_count += sentence_token_count

        if current_chunk:
            chunks.append(''.join(current_chunk))
        return chunks

tes = {'objects': [['Country', 'Kazakhstan', [['Қазақстан', 'kz'], ['Kazakhstan', 'en'], ['Казахстан', 'ru']]], ['Lake', 'Caspian Sea', [['Каспийское море', 'kz'], ['Caspian Sea', 'en'], ['Каспийское море', 'ru']]], ['Lake', 'Aral Sea', [['Аральское море', 'kz'], ['Aral Sea', 'en'], ['Аральское море', 'ru']]], ['Lake', 'Lake Balkhash', [['Балхаш', 'kz'], ['Lake Balkhash', 'en'], ['Озеро Балхаш', 'ru']]], ['Mountain', 'Khan Tengri', [['Хан-Тенгри', 'kz'], ['Khan Tengri', 'en'], ['Хан-Тенгри', 'ru']]], ['Mountain', 'Ural Mountains', [['Уральские горы', 'kz'], ['Ural Mountains', 'en'], ['Уральские горы', 'ru']]], ['River', 'Irtish', [['Иртыш', 'kz'], ['Irtish', 'en'], ['Иртыш', 'ru']]], ['River', 'Ural River', [['Урал', 'kz'], ['Ural River', 'en'], ['Урал', 'ru']]], ['River', 'Syr Darya', [['Сырдарья', 'kz'], ['Syr Darya', 'en'], ['Сырдарья', 'ru']]], ['River', 'Ili', [['Или', 'kz'], ['Ili', 'en'], ['Или', 'ru']]], ['Region', 'West Kazakhstan Region', [['Батыс Қазақстан облысы', 'kz'], ['West Kazakhstan Region', 'en'], ['Западно-Казахстанская область', 'ru']]], ['Region', 'Atyrau Region', [['Атырау облысы', 'kz'], ['Atyrau Region', 'en'], ['Атырауская область', 'ru']]], ['Region', 'Aktobe Region', [['Ақтөбе облысы', 'kz'], ['Aktobe Region', 'en'], ['Актюбинская область', 'ru']]]], 'object properties': [['hasBorder', ['Kazakhstan', 'Russia']], ['hasBorder', ['Kazakhstan', 'Uzbekistan']], ['hasBorder', ['Kazakhstan', 'China']], ['hasBorder', ['Kazakhstan', 'Kyrgyzstan']], ['hasBorder', ['Kazakhstan', 'Turkmenistan']], ['located', ['Caspian Sea', 'Kazakhstan']], ['located', ['Aral Sea', 'Kazakhstan']], ['located', ['Lake Balkhash', 'Kazakhstan']], ['located', ['Irtish', 'Kazakhstan']], ['located', ['Ural River', 'Kazakhstan']], ['located', ['Syr Darya', 'Kazakhstan']], ['located', ['Ili', 'Kazakhstan']], ['consists', ['West Kazakhstan Region', 'Caspian Sea']], ['consists', ['Atyrau Region', 'Caspian Sea']], ['consists', ['Aktobe Region', 'Ural Mountains']], ['isPart', ['Kazakhstan', 'West Kazakhstan Region']], ['isPart', ['Kazakhstan', 'Atyrau Region']], ['isPart', ['Kazakhstan', 'Aktobe Region']]], 'data properties': [['square', ['Kazakhstan', 2724900.0]], ['population', ['Kazakhstan', 18776707]]]}

adapter = DefaultJsonAdapter()
adapter.map_json(tes)
# def make_consistent(threshold, counters_dict):
#     result = {'objects': {}, 'object_properties': {}, 'data_properties': {}}
#     for entity_type, classes in counters_dict.items():
#         for class_name, entities in classes.items():
#             for entity, count in entities.items():
#                 if count >= threshold:
#                     if class_name not in result[entity_type]:
#                         result[entity_type][class_name] = {entity}
#                     result[entity_type][class_name].add(entity)
#     global_state_manager.trigger_callback('update_ChatGPT_response_tab', result)
#     return result
#
# make_consistent(2, counters_dict)
# def choice_to_tuple(choice):
#     try:
#         if choice.get('objects'):
#             tuple_choice = {}
#             current_set = set()
#             for obj in choice['objects']:
#                 for i in range(len(obj[2])):
#                     obj[2][i] = tuple(obj[2][i])
#                 obj[2] = tuple(obj[2])
#                 obj = tuple(obj)
#                 current_set.add(tuple(obj))
#             tuple_choice['objects'] = current_set
#             current_set = set()
#             if choice.get('object_properties'):
#                 for obj_prop in choice['object_properties']:
#                     obj_prop[1] = tuple(obj_prop[1])
#                     obj_prop = tuple(obj_prop)
#                     current_set.add(obj_prop)
#                 tuple_choice['object_properties'] = current_set
#                 current_set = set()
#             if choice.get('data_properties'):
#                 for data_prop in choice['data_properties']:
#                     data_prop[1] = tuple(data_prop[1])
#                     data_prop = tuple(data_prop)
#                     current_set.add(data_prop)
#                 tuple_choice['data_properties'] = current_set
#     except Exception as e:
#         raise WrongJsonStructureError(choice)
#
#     return tuple_choice


# def check_and_parse_gpt_response(response, threshold):
#
#     current_result = {'objects': Counter(), 'object_properties': Counter(), 'data_properties': Counter()}
#     result = {'objects': set(), 'object_properties': set(), 'data_properties': set()}
#     for choice in response:
#         try:
#             json_choice = extract_json(choice)
#             tuple_choice = choice_to_tuple(json_choice)
#         except (json.JSONDecodeError, JsonNotFountError) as e:
#             logging.error("An error occurred while decoding ChatGPT response", exc_info=True)
#             continue
#         except WrongJsonStructureError as e:
#             logging.error("An error occurred while parsing decoded ChatGPT JSON response", exc_info=True)
#             continue
#
#         for entity_type, individuals in tuple_choice.items():
#             current_result[entity_type].update(individuals)
#         # for entity_type, classes_set in hashable_choice.items():
#         #     for cls, individuals in classes_set.items():
#         #         if current_result[entity_type].get(cls):
#         #             current_result[entity_type][cls].update(tuple(individual) for individual in individuals)
#         #         else:
#         #             current_result[entity_type][cls] = Counter(individuals)
#
#     for entity_type, entities_counter in current_result.items():
#         for entity, count in entities_counter.items():
#             if count >= threshold:
#                 result[entity_type].add(entity)
#
#     if result is None:
#         raise InconsistentChatGptResponse(response)
#     print("Individuals to add")
#     print(result)
#     return result
