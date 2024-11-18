import logging

from owlready2 import Ontology, locstr, ObjectPropertyClass

from src.repository.kb_repository import KBRepository
from src.gui.state_manager import global_state_manager


class OntologyOwlready2Repository(KBRepository):
    def __init__(self, onto: Ontology, save_ontology_path: str):
        self.onto = onto
        self.individuals = {}
        self.save_ontology_path = save_ontology_path
        self.logger = logging.getLogger("app_logger")
        self.param_setters = {
            1: self.set_labels
        }

    def set_labels(self, individual, labels):
        for label in labels:
            individual.label.append(locstr(label[0], lang=label[1]))

    def save_ontology(self):
        self.onto.save(self.save_ontology_path)
        for individual in self.individuals.values():
            global_state_manager.trigger_callback('update_added_individuals_tab', self.descript_individual(individual))
        global_state_manager.trigger_callback('update_individuals_count', len(self.individuals))
        self.individuals = {}

    def add_individuals(self, entities_dict: dict):
        if entities_dict['objects'] is not None:
            self.create_individuals(entities_dict['objects'])
            if entities_dict['object_properties'] is not None:
                self.add_object_properties(entities_dict['object_properties'])
            if entities_dict['data_properties'] is not None:
                self.add_data_properties(entities_dict['data_properties'])
            self.save_ontology()

    def create_individuals(self, individuals_dict: dict):
        for class_name, individuals_data in individuals_dict.items():
            with self.onto:
                obj_class = getattr(self.onto, class_name, None)
                if obj_class is None:
                    self.logger.error(f"Class '{class_name}' not found in ontology.")
                    continue
                for individual_data in individuals_data:
                    individual = obj_class(individual_data[0])
                    self.individuals[individual_data[0]] = individual
                    for i in range(1, len(individual_data)):
                        self.param_setters[i](individual, individual_data[i])

    def add_object_properties(self, properties_data: dict):
        for property_name, properties_data in properties_data.items():
            with self.onto:
                prop = getattr(self.onto, property_name, None)
                if prop is None:
                    self.logger.error(f"Object property '{property_name}' not found in ontology.")
                    global_state_manager.trigger_callback('update_errors_tab',
                                                          f"Object property '{property_name}' not found in ontology.")

                for property_data in properties_data:
                    subject_name, object_name = property_data
                    if subject_name not in self.individuals:
                        self.logger.error(f"Subject '{subject_name}' for '{property_name}' not found in individuals.")
                        global_state_manager.trigger_callback('update_errors_tab',
                                                              f"Subject '{subject_name}' for '{property_name}' not found in individuals.")
                        continue
                    if object_name not in self.individuals:
                        self.logger.error(f"Object '{object_name}' for '{property_name}' not found in individuals.")
                        global_state_manager.trigger_callback('update_errors_tab',
                                                              f"Object '{object_name}' for '{property_name}' not found in individuals.")
                        continue

                    prop[self.individuals[subject_name]].append(self.individuals[object_name])
                    global_state_manager.trigger_callback('update_obj_props_count', 1)

    def add_data_properties(self, properties_data: dict):
        for property_name, properties_data in properties_data.items():
            with self.onto:
                data_prop = getattr(self.onto, property_name, None)
                if data_prop is None:
                    self.logger.error(f"Data property '{property_name}' not found in ontology.")
                    continue
                for property_data in properties_data:
                    object_name, value = property_data
                    if object_name not in self.individuals:
                        self.logger.error(f"Object '{object_name}' for '{property_name}' not found in individuals.")
                        global_state_manager.trigger_callback('update_errors_tab',
                                                              f"Object '{object_name}' for '{property_name}' not found in individuals.")
                        continue

                    try:
                        data_prop[self.individuals[object_name]] = [value]
                        global_state_manager.trigger_callback('update_data_props_count', 1)
                    except ValueError as e:
                        self.logger.error(f"Type validation error for '{object_name}': {e}")
                        global_state_manager.trigger_callback('update_errors_tab', f"Type validation error for '{object_name}': {e}")
                        continue

    def descript_individual(self, individual):
        individual_name = individual.name
        description = f"Individual: {individual_name}\n"

        types = individual.is_a
        if types:
            types_str = ', '.join(cls.name for cls in types)
            description += f"  Types: {types_str}\n"

        properties = individual.get_properties()

        for prop in properties:
            values = prop[individual]
            if values:
                if isinstance(prop, ObjectPropertyClass):
                    value_names = ', '.join(v.name for v in values)
                else:
                    value_names = ', '.join(str(v) for v in values)
                description += f"  {prop.name}: {value_names}\n"

        return description

