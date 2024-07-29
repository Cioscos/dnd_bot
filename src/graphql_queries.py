CATEGORY_TO_QUERY_MAP = {
    'monsters': """query Monster($index: String) {
  monster(index: $index) {
    name
    alignment
    challenge_rating
    charisma
    constitution
    damage_immunities
    damage_resistances
    damage_vulnerabilities
    desc
    dexterity
    hit_dice
    hit_points
    hit_points_roll
    image
    index
    intelligence
    languages
    proficiency_bonus
    size
    speed {
      burrow
      climb
      fly
      hover
      swim
      walk
    }
    strength
    subtype
    type
    wisdom
    xp
    actions {
      name
      desc
      dc {
        type {
          name
          full_name
          desc
          skills {
            name
            desc
          }
        }
        value
        success
      }
      damage {
        type
        dc {
          type {
            name
            full_name
            desc
          }
          value
          success
        }
        damage_type {
          name
          desc
        }
        damage_dice
        choose
      }
      attacks {
        name
        dc {
          type {
            name
            full_name
            desc
          }
          value
          success
        }
      }
      attack_bonus
      options {
        type
        choose
      }
      multiattack_type
      actions {
        type
        action_name
        count
      }
      usage {
        dice
        min_value
        rest_types
        times
        type
      }
      action_options {
        choose
        type
        from {
          option_set_type
          options {
            ... on ActionOption {
              action_name
              count
              option_type
              type
            }
            ... on MultipleActionOption {
              items {
                action_name
                count
                option_type
                type
              }
              option_type
            }
          }
        }
      }
    }
    armor_class {
      value
      desc
      condition {
        name
        desc
      }
      armor {
        name
        desc
        armor_class {
          max_bonus
          dex_bonus
          base
        }
        stealth_disadvantage
        str_minimum
        weight
        armor_category {
          name
        }
      }
      spell {
        name
      }
    }
    condition_immunities {
      name
      desc
    }
    legendary_actions {
      name
      desc
      dc {
        value
        success
        type {
          name
          full_name
          desc
          skills {
            name
            desc
            ability_score {
              full_name
              desc
              name
            }
          }
        }
      }
      damage {
        damage_type {
          name
          desc
        }
        damage_dice
      }
    }
    special_abilities {
      name
      desc
      usage {
        dice
        min_value
        times
        rest_types
        type
      }
      dc {
        value
        success
        type {
          full_name
          desc
        }
      }
      damage {
        damage_dice
        damage_type {
          name
          desc
        }
      }
    }
    reactions {
      name
      desc
      dc {
        success
        value
        type {
          full_name
          desc
        }
      }
    }
    senses {
      blindsight
      darkvision
      passive_perception
      tremorsense
      truesight
    }
    proficiencies {
      value
      proficiency {
        name
      }
    }
    forms {
      name
      type
      alignment
      image
    }
  }
}"""
}

# query Monster($index: String) {
#   monster(index: $index) {
#     name
#     alignment
#     challenge_rating
#     charisma
#     constitution
#     damage_immunities
#     damage_resistances
#     damage_vulnerabilities
#     desc
#     dexterity
#     hit_dice
#     hit_points
#     hit_points_roll
#     image
#     index
#     intelligence
#     languages
#     proficiency_bonus
#     size
#     speed {
#       burrow
#       climb
#       fly
#       hover
#       swim
#       walk
#     }
#     strength
#     subtype
#     type
#     wisdom
#     xp
#     actions {
#       name
#       desc
#       dc {
#         type {
#           name
#           full_name
#           desc
#           skills {
#             name
#             desc
#           }
#         }
#         value
#         success
#       }
#       damage {
#         type
#         dc {
#           type {
#             name
#             full_name
#             desc
#           }
#           value
#           success
#         }
#         damage_type {
#           name
#           desc
#         }
#         damage_dice
#         choose
#       }
#       attacks {
#         name
#         dc {
#           type {
#             name
#             full_name
#             desc
#           }
#           value
#           success
#         }
#       }
#       attack_bonus
#       options {
#         type
#         choose
#       }
#       multiattack_type
#       actions {
#         type
#         action_name
#         count
#       }
#       usage {
#         dice
#         min_value
#         rest_types
#         times
#         type
#       }
#     }
#     armor_class {
#       value
#       desc
#       condition {
#         name
#         desc
#       }
#       armor {
#         name
#         desc
#         armor_class {
#           max_bonus
#           dex_bonus
#           base
#         }
#         stealth_disadvantage
#         str_minimum
#         weight
#         armor_category {
#           name
#         }
#       }
#       spell {
#         name
#       }
#     }
#     condition_immunities {
#       name
#       desc
#     }
#     legendary_actions {
#       name
#       desc
#       dc {
#         value
#         success
#         type {
#           name
#           full_name
#           desc
#           skills {
#             name
#             desc
#             ability_score {
#               full_name
#               desc
#               name
#             }
#           }
#         }
#       }
#       damage {
#         damage_type {
#           name
#           desc
#         }
#         damage_dice
#       }
#     }
#     special_abilities {
#       name
#       desc
#       usage {
#         dice
#         min_value
#         times
#         rest_types
#         type
#       }
#       dc {
#         value
#         success
#         type {
#           full_name
#           desc
#         }
#       }
#       damage {
#         damage_dice
#         damage_type {
#           name
#           desc
#         }
#       }
#     }
#     reactions {
#       name
#       desc
#       dc {
#         success
#         value
#         type {
#           full_name
#           desc
#         }
#       }
#     }
#     senses {
#       blindsight
#       darkvision
#       passive_perception
#       tremorsense
#       truesight
#     }
#     proficiencies {
#       value
#       proficiency {
#         name
#       }
#     }
#     forms {
#       name
#       type
#       alignment
#       image
#     }
#   }
# }
