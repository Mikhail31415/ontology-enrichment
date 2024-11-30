def process_comments(comments):
    ignore = True
    additional_text = None
    for comment in comments:
        if comment.startswith("!"):
            additional_text = comment[1:].strip() if comment[1:].strip() else None
            ignore = False
            break
    return ignore, additional_text

def class_is_subclass_of(cls, classes):
    for potential_an in classes:
        if potential_an in cls.ancestors():
            return True
    return False

def get_class_list(onto):
    class_description_list = []
    class_list = []
    for cls in onto.classes():
        ignore, additional_text = process_comments(cls.comment)
        if ignore:
            continue
        class_name = cls.name
        class_list.append(cls)
        if additional_text:
            class_name += f" ({additional_text})"
        class_description_list.append(class_name)
    return class_description_list, class_list

def get_relation_list(onto, class_list):
    relation_list = []

    for obj_prop in onto.object_properties():
        prop_domain_classes = []
        prop_range_classes = []

        ignore, additional_text = process_comments(obj_prop.comment)
        if ignore:
            continue
        relation_name = obj_prop.name
        if additional_text:
            relation_name += f" ({additional_text})"

        for cls in class_list:
            if class_is_subclass_of(cls, obj_prop.domain):
                prop_domain_classes.append(cls)

        for cls in class_list:
            if class_is_subclass_of(cls, obj_prop.range):
                prop_range_classes.append(cls)

        domain_str = ", ".join(prop_domain_class.name for prop_domain_class in prop_domain_classes) if prop_domain_classes else ""
        range_str = ", ".join(prop_range_class.name for prop_range_class in prop_range_classes) if prop_range_classes else ""

        if domain_str and range_str:
            relation_list.append(f"{relation_name}: relates individuals of {domain_str} to individuals of {range_str}")

    return relation_list

def get_data_property_list(onto, class_list):
    data_property_list = []

    for data_prop in onto.data_properties():
        prop_domain_classes = []

        ignore, additional_text = process_comments(data_prop.comment)
        if ignore:
            continue
        property_name = data_prop.name
        if additional_text:
            property_name += f" ({additional_text})"

        for cls in class_list:
            if class_is_subclass_of(cls, data_prop.domain):
                prop_domain_classes.append(cls)

        domain_str = ", ".join(prop_domain_class.name for prop_domain_class in prop_domain_classes) if prop_domain_classes else ""
        type_str = ", ".join([range_class.__name__ for range_class in data_prop.range]) if data_prop.range else ""

        if domain_str and type_str:
            data_property_list.append(f"{property_name}: applies to individuals of {domain_str}, values must be of type {type_str}")

    return data_property_list

def generate_prompt(onto):
    class_description_list, class_list = get_class_list(onto)
    relation_list = get_relation_list(onto, class_list)
    data_property_list = get_data_property_list(onto, class_list)

    prompt = "Select all individuals of the following classes mentioned in the text:\n"
    prompt += ", ".join(class_description_list) + "\n"
    prompt += "Return them in three languages (Kazakh, English, Russian) as a list according to this format:\n"
    prompt += '"objects": [["class name", "individual name in en", [["individual name in kz", "kz"], ["individual name in en", "en"], ["individual name in ru", "ru"]]],]\n\n'

    if relation_list:
        prompt += "Additionally, identify any relationships between the found individuals mentioned in the text, using only the following possible relations:\n"
        prompt += "\n".join(relation_list) + "\n"
        prompt += "Return them as a list in this format:\n"
        prompt += '"object_properties": [["relationship name", ["subject individual name in english", "object individual name in english"]],]\n\n'
    if data_property_list:
        prompt += "Finally, based on the text, identify any data properties for the found individuals mentioned in the text, using only the following possible data properties:\n"
        prompt += ", ".join(data_property_list) + "\n"
        prompt += "Return them as a list in this format:\n"
        prompt += '"data_properties": [["data property name", ["individual name in english", "value"]],]\n'
    prompt += 'Important: Do not include any information from that instruction in your response. Your response should contain **only** the data explicitly extracted from the text and formatted as described above.'

    return prompt

# from owlready2 import get_ontology
#
# ontology_path = "C:\\Users\\Михаил\\Desktop\\ontology\\geo.owl"
# prompt = generate_prompt(get_ontology(ontology_path).load())
# print(prompt)

    # prompt = "Select all individuals of the following classes mentioned in the text:\n"
    # prompt += ", ".join(class_description_list) + "\n"
    # prompt += "and return them as a list according to this format:\n"
    # prompt += '"objects": {"class name": {["individual name in en", [["individual name in kz", "kz"], ["individual name in en", "en"], ["individual name in ru", "ru"]]],},}\n'
    #
    # if relation_list:
    #     prompt += "Additionally, based on the text, identify any relationships between the found individuals using the following possible relations:\n"
    #     prompt += "\n".join(relation_list) + "\n"
    #     prompt += "and return them as a list in this format:\n"
    #     prompt += '"object_properties": {"relationship name": {["subject individual name in english", "object individual name in english"],},}\n'
    # if data_property_list:
    #     prompt += "\nFinally, identify the following data properties for the found individuals:\n"
    #     prompt += ", ".join(data_property_list) + "\n"
    #     prompt += "and return them as a list in this format:\n"
    #     prompt += '"data_properties": {"data property name": {["individual name in english", "value"],},}\n'
    # print(prompt)
    # return prompt