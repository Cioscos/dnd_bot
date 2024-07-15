from typing import Any, Dict

from src.model.APIResource import APIResource
from src.model.AbilityScore import AbilityScore
from src.model.ClassResource import ClassResource
from src.model.subclasses import MultiClassing, Spellcasting, SpellcastingInfo, StartingEquipmentOption, \
    StartingEquipment, ProficiencyChoice, Option, EquipmentCategory, Choice, OptionItem


def parse_ability_score(data: Dict[str, Any]) -> AbilityScore:
    skills = [APIResource(skill['index'], skill['name'], skill['url']) for skill in data.get('skills', [])]
    return AbilityScore(
        data['index'],
        data['name'],
        data['url'],
        data['full_name'],
        data['desc'],
        skills
    )


def parse_option(data: Dict[str, Any]) -> Option:
    item = None
    if 'item' in data:
        item = OptionItem(data['item']['index'], data['item']['name'], data['item']['url'])

    choice = None
    if 'choice' in data:
        choice = Choice(data['choice']['desc'], data['choice']['choose'], data['choice']['type'],
                        EquipmentCategory(data['choice']['from']['equipment_category']['index'],
                                          data['choice']['from']['equipment_category']['name'],
                                          data['choice']['from']['equipment_category']['url']))

    return Option(
        option_type=data['option_type'],
        item=item,
        count=data.get('count'),
        choice=choice
    )


def parse_proficiency_choice(data: Dict[str, Any]) -> ProficiencyChoice:
    options = [parse_option(option) for option in data['from']['options']]
    return ProficiencyChoice(
        desc=data['desc'],
        choose=data['choose'],
        type=data['type'],
        options=options
    )


def parse_starting_equipment(data: Dict[str, Any]) -> StartingEquipment:
    equipment = APIResource(data['equipment']['index'], data['equipment']['name'], data['equipment']['url'])
    return StartingEquipment(
        equipment=equipment,
        quantity=data['quantity']
    )


def parse_starting_equipment_option(data: Dict[str, Any]) -> StartingEquipmentOption:
    options = [parse_option(option) for option in data['from']['options']]
    return StartingEquipmentOption(
        desc=data['desc'],
        choose=data['choose'],
        type=data['type'],
        options=options
    )


def parse_spellcasting_info(data: Dict[str, Any]) -> SpellcastingInfo:
    return SpellcastingInfo(
        name=data['name'],
        desc=data['desc']
    )


def parse_spellcasting(data: Dict[str, Any]) -> Spellcasting:
    spellcasting_ability = APIResource(data['spellcasting_ability']['index'], data['spellcasting_ability']['name'],
                                       data['spellcasting_ability']['url'])
    info = [parse_spellcasting_info(info_item) for info_item in data['info']]
    return Spellcasting(
        level=data['level'],
        spellcasting_ability=spellcasting_ability,
        info=info
    )


def parse_multi_classing(data: Dict[str, Any]) -> MultiClassing:
    proficiencies = [APIResource(prof['index'], prof['name'], prof['url']) for prof in data['proficiencies']]
    return MultiClassing(
        prerequisites=data['prerequisites'],
        proficiencies=proficiencies
    )


def parse_class(data: Dict[str, Any]) -> ClassResource:
    proficiency_choices = [parse_proficiency_choice(choice) for choice in data['proficiency_choices']]
    proficiencies = [APIResource(prof['index'], prof['name'], prof['url']) for prof in data['proficiencies']]
    saving_throws = [APIResource(st['index'], st['name'], st['url']) for st in data['saving_throws']]
    starting_equipment = [parse_starting_equipment(equip) for equip in data['starting_equipment']]
    starting_equipment_options = [parse_starting_equipment_option(option) for option in
                                  data['starting_equipment_options']]
    subclasses = [APIResource(subclass['index'], subclass['name'], subclass['url']) for subclass in data['subclasses']]
    spellcasting = parse_spellcasting(data['spellcasting'])
    multi_classing = parse_multi_classing(data['multi_classing'])

    return ClassResource(
        index=data['index'],
        name=data['name'],
        url=data['url'],
        hit_die=data['hit_die'],
        proficiency_choices=proficiency_choices,
        proficiencies=proficiencies,
        saving_throws=saving_throws,
        starting_equipment=starting_equipment,
        starting_equipment_options=starting_equipment_options,
        class_levels=data['class_levels'],
        multi_classing=multi_classing,
        subclasses=subclasses,
        spellcasting=spellcasting,
        spells=data['spells']
    )
