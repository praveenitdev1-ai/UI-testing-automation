"""
Step 07: Frontend Wiring Plan Generator
Merges TSX metadata with application config to create a comprehensive wiring plan.
Uses deterministic label-based matching for field mapping.

Usage:
    python step_07_frontend_wiring_gemini_llm.py <app_config.json> <tsx_metadata.json> <output_wired_ui.json>

Example:
    python step_07_frontend_wiring_gemini_llm.py application_config.json tsx_metadata.json wired_ui.json
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


class MatchConfidence(Enum):
    """Match confidence levels in priority order (lower = better)."""
    EXACT_LABEL = 1
    EXACT_ID = 2
    LABEL_IN_PLACEHOLDER = 3
    NORMALIZED_ID = 4
    LABEL_CONTAINS = 5
    LABEL_CONTAINED_BY = 6
    WORD_START_MATCH = 7
    SYNONYM_MATCH = 8
    SECTION_CONTEXT = 9
    NO_MATCH = 99


@dataclass
class FieldMapping:
    """Represents a mapping between TSX field and config field."""
    tsx_id: str
    tsx_label: Optional[str]
    config_field_id: str
    config_label: str
    config_binding: str
    confidence: str
    match_reason: str
    validations: List[Dict[str, Any]] = field(default_factory=list)
    error_messages: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tsx_id': self.tsx_id,
            'tsx_label': self.tsx_label,
            'config_field_id': self.config_field_id,
            'config_label': self.config_label,
            'config_binding': self.config_binding,
            'confidence': self.confidence,
            'match_reason': self.match_reason,
            'validations': self.validations,
            'error_messages': self.error_messages
        }


@dataclass
class HandlerMapping:
    """Represents a mapping between TSX handler and config action."""
    tsx_function_name: str
    tsx_button_text: Optional[str]
    story_id: str
    config_action: str
    target_api_endpoint: str
    target_api_method: str
    target_entity: str
    confidence: str
    match_reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass 
class ScreenMapping:
    """Represents a complete screen mapping."""
    tsx_screen_name: str
    story_id: str
    story_title: str
    screen_name: str
    field_mappings: List[FieldMapping]
    handler_mappings: List[HandlerMapping]
    primary_entity: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tsx_screen_name': self.tsx_screen_name,
            'story_id': self.story_id,
            'story_title': self.story_title,
            'screen_name': self.screen_name,
            'field_mappings': [f.to_dict() for f in self.field_mappings],
            'handler_mappings': [h.to_dict() for h in self.handler_mappings],
            'primary_entity': self.primary_entity
        }


class WiringPlanner:
    """
    Creates wiring plan by matching TSX elements to application config.
    Uses deterministic, label-based matching with configurable fuzzy matching rules.
    """
    
    def __init__(self, app_config: Dict[str, Any], tsx_metadata: Dict[str, Any]):
        self.config = app_config
        self.tsx_metadata = tsx_metadata
        self.screen_layouts = app_config.get('screen_layouts', [])
        self.entities = {e['name']: e for e in app_config.get('entities', [])}
        self.validation_rules = app_config.get('validation_rules', [])
        self.error_messages = app_config.get('error_messages', [])
        self.field_validations = app_config.get('field_validations', [])
        self.matching_config = self._load_matching_config()
        
        # Load acceptance criteria from config
        self.acceptance_criteria = app_config.get('acceptance_criteria', [])
        self.ac_by_story = self._group_ac_by_story()
        
        # Pass through ac_coverage from Step 06 if available
        self.ac_coverage_from_step06 = tsx_metadata.get('ac_coverage', {})
    
    def _group_ac_by_story(self) -> Dict[str, List[Dict]]:
        """Group acceptance criteria by source_story_id."""
        ac_by_story = {}
        for ac in self.acceptance_criteria:
            story_id = ac.get('source_story_id', '')
            if story_id not in ac_by_story:
                ac_by_story[story_id] = []
            ac_by_story[story_id].append(ac)
        return ac_by_story
    
    def _load_matching_config(self) -> Dict[str, Any]:
        """Load field matching configuration from JSON file."""
        config_path = Path(__file__).parent / 'field_matching_config.json'
        default_config = {
            "abbreviations": {
                "dept": "department",
                "desc": "description",
                "qty": "quantity",
                "num": "number"
            },
            "label_synonyms": {},
            "ignore_prefixes": ["filter by", "select", "enter", "choose"],
            "version": "default"
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    print(f"[INFO] Loaded field matching config v{loaded.get('version', 'unknown')}")
                    return loaded
            except Exception as e:
                print(f"[WARN] Failed to load field_matching_config.json: {e}, using defaults")
        else:
            print(f"[INFO] No field_matching_config.json found, using default matching rules")
        
        return default_config
        
    def generate_wiring_plan(self) -> Dict[str, Any]:
        """Generate complete wiring plan."""
        screen_mappings = []
        unmapped_fields = []
        unmapped_handlers = []
        
        # Build screen name to story mapping from config
        screen_to_story = self._build_screen_to_story_map()
        
        # Process each TSX screen
        for tsx_screen in self.tsx_metadata.get('screens', []):
            tsx_screen_name = tsx_screen['component_name']
            
            # Find matching story/screen in config
            story_match = self._find_story_for_screen(tsx_screen_name, screen_to_story)
            
            if story_match:
                screen_layout = story_match['screen_layout']
                
                # Map fields
                field_mappings, unmatched = self._map_fields(
                    tsx_screen.get('fields', []),
                    screen_layout
                )
                unmapped_fields.extend(unmatched)
                
                # Map handlers
                handler_mappings, unmatched_handlers = self._map_handlers(
                    tsx_screen.get('handlers', []),
                    screen_layout,
                    story_match['story_id']
                )
                unmapped_handlers.extend(unmatched_handlers)
                
                # Determine primary entity
                primary_entity = self._determine_primary_entity(screen_layout)
                
                screen_mappings.append(ScreenMapping(
                    tsx_screen_name=tsx_screen_name,
                    story_id=story_match['story_id'],
                    story_title=story_match['story_title'],
                    screen_name=screen_layout.get('screen_name', ''),
                    field_mappings=field_mappings,
                    handler_mappings=handler_mappings,
                    primary_entity=primary_entity
                ))
            else:
                # No story match - warn and mark all elements as unmapped
                print(f"[WARN] No User Story mapping found for screen: {tsx_screen_name}")
                for f in tsx_screen.get('fields', []):
                    unmapped_fields.append({
                        'tsx_id': f['tsx_id'],
                        'screen': tsx_screen_name,
                        'reason': 'no_story_match_for_screen'
                    })
        
        # Map top-level handlers
        top_level_mappings = self._map_top_level_handlers(
            self.tsx_metadata.get('top_level_handlers', [])
        )
        
        # Build entity service definitions
        entity_services = self._build_entity_services()
        
        return {
            'metadata': {
                'app_name': self.config.get('metadata', {}).get('app_name', 'App'),
                'generated_by': 'step_07_frontend_wiring',
                'version': '2.0-deterministic'
            },
            'screen_mappings': [sm.to_dict() for sm in screen_mappings],
            'top_level_handlers': top_level_mappings,
            'entity_services': entity_services,
            'mock_data_removal': self.tsx_metadata.get('mock_data_locations', []),
            'unmapped_elements': {
                'fields': unmapped_fields,
                'handlers': unmapped_handlers
            },
            'validation_summary': self._build_validation_summary(),
            'acceptance_criteria_coverage': self._build_ac_coverage_with_mapping(screen_mappings)
        }
    
    def _build_screen_to_story_map(self) -> Dict[str, Dict]:
        """Build mapping from screen names to story info."""
        mapping = {}
        
        for layout in self.screen_layouts:
            story_id = layout.get('story_id', '')
            screen_name = layout.get('screen_name', '')
            story_title = layout.get('story_title', '')
            
            # Create multiple keys for flexible matching
            keys = [
                screen_name.lower().replace(' ', ''),
                story_title.lower().replace(' ', ''),
                story_id.lower().replace(' ', ''),
            ]
            
            for key in keys:
                if key:
                    mapping[key] = {
                        'story_id': story_id,
                        'story_title': story_title,
                        'screen_layout': layout
                    }
        
        return mapping
    
    def _find_story_for_screen(
        self, 
        tsx_screen_name: str,
        screen_to_story: Dict[str, Dict]
    ) -> Optional[Dict]:
        """Find matching story for a TSX screen name."""
        
        # Define screen to story mapping patterns
        # This is based on component naming convention, not hardcoded IDs
        screen_patterns = {
            'worklist': ['add item to worklist', 'scan pos tracking', 'rtv worklist'],
            'maintenance': ['nsi maintenance', 'salvage workflow', 'reverse'],
            'dashboard': ['manager dashboard'],
            'inquiry': ['inquiry'],
            'salvage': ['salvage revenue'],
        }
        
        tsx_name_lower = tsx_screen_name.lower()
        
        # Find which pattern group this screen belongs to
        matched_patterns = []
        for pattern_key, patterns in screen_patterns.items():
            if pattern_key in tsx_name_lower:
                matched_patterns.extend(patterns)
        
        # Search for matching story
        for pattern in matched_patterns:
            pattern_normalized = pattern.replace(' ', '')
            if pattern_normalized in screen_to_story:
                return screen_to_story[pattern_normalized]
        
        # Fallback: direct key lookup
        tsx_normalized = tsx_name_lower.replace('screen', '').replace(' ', '')
        for key, value in screen_to_story.items():
            if tsx_normalized in key or key in tsx_normalized:
                return value
        
        return None
    
    def _map_fields(
        self,
        tsx_fields: List[Dict],
        screen_layout: Dict
    ) -> Tuple[List[FieldMapping], List[Dict]]:
        """Map TSX fields to config fields using deterministic matching."""
        mappings = []
        unmapped = []
        
        # Extract all config fields from screen layout
        config_fields = []
        for section in screen_layout.get('layout_sections', []):
            section_title = section.get('title', '')
            for field in section.get('fields', []):
                field_copy = field.copy()
                field_copy['section_title'] = section_title
                config_fields.append(field_copy)
        
        # Track which config fields have been matched
        matched_config_ids = set()
        
        for tsx_field in tsx_fields:
            match = self._find_best_field_match(tsx_field, config_fields, matched_config_ids)
            
            if match:
                config_field, confidence, reason = match
                matched_config_ids.add(config_field['id'])
                
                # Get validations for this field
                validations = self._get_field_validations(
                    config_field['id'],
                    screen_layout.get('story_id', '')
                )
                
                # Get error messages
                error_msgs = self._get_field_error_messages(
                    config_field['id'],
                    screen_layout.get('story_id', '')
                )
                
                mappings.append(FieldMapping(
                    tsx_id=tsx_field['tsx_id'],
                    tsx_label=tsx_field.get('label'),
                    config_field_id=config_field['id'],
                    config_label=config_field.get('label', ''),
                    config_binding=config_field.get('binding', ''),
                    confidence=confidence.name,
                    match_reason=reason,
                    validations=validations,
                    error_messages=error_msgs
                ))
            else:
                print(f"[WARN] No config match for TSX field: tsx_id='{tsx_field['tsx_id']}' label='{tsx_field.get('label')}' (story: {screen_layout.get('story_id', 'unknown')})")
                unmapped.append({
                    'tsx_id': tsx_field['tsx_id'],
                    'tsx_label': tsx_field.get('label'),
                    'reason': 'no_config_match'
                })
        
        return mappings, unmapped
    
    def _find_best_field_match(
        self,
        tsx_field: Dict,
        config_fields: List[Dict],
        already_matched: set
    ) -> Optional[Tuple[Dict, MatchConfidence, str]]:
        """Find best matching config field using deterministic rules with fuzzy matching."""
        
        tsx_id = tsx_field.get('tsx_id', '').lower()
        tsx_label = (tsx_field.get('label') or '').lower().strip()
        tsx_placeholder = (tsx_field.get('placeholder') or '').lower()
        
        # Strip ignore prefixes from tsx_label for better matching
        tsx_label_stripped = tsx_label
        for prefix in self.matching_config.get('ignore_prefixes', []):
            if tsx_label_stripped.startswith(prefix):
                tsx_label_stripped = tsx_label_stripped[len(prefix):].strip()
                break
        
        candidates = []
        
        for config_field in config_fields:
            config_id = config_field.get('id', '')
            
            # Skip already matched fields
            if config_id in already_matched:
                continue
            
            config_label = config_field.get('label', '').lower().strip()
            
            # Rule 1: Exact label match (highest priority)
            if tsx_label and config_label and tsx_label == config_label:
                candidates.append((
                    config_field,
                    MatchConfidence.EXACT_LABEL,
                    f"Exact label match: '{tsx_label}'"
                ))
                continue
            
            # Rule 2: Exact ID match
            if tsx_id == config_id.lower():
                candidates.append((
                    config_field,
                    MatchConfidence.EXACT_ID,
                    f"Exact ID match: '{tsx_id}'"
                ))
                continue
            
            # Rule 3: Config label in TSX placeholder
            if config_label and config_label in tsx_placeholder:
                candidates.append((
                    config_field,
                    MatchConfidence.LABEL_IN_PLACEHOLDER,
                    f"Label '{config_label}' found in placeholder"
                ))
                continue
            
            # Rule 4: Normalized ID match
            tsx_normalized = self._normalize_field_id(tsx_id)
            config_normalized = self._normalize_field_id(config_id)
            
            if tsx_normalized and config_normalized and tsx_normalized == config_normalized:
                candidates.append((
                    config_field,
                    MatchConfidence.NORMALIZED_ID,
                    f"Normalized ID match: '{tsx_id}' -> '{config_id}'"
                ))
                continue
            
            # Rule 5: Label contains (config label in tsx label or stripped label)
            if config_label and len(config_label) >= 3:
                if config_label in tsx_label or config_label in tsx_label_stripped:
                    candidates.append((
                        config_field,
                        MatchConfidence.LABEL_CONTAINS,
                        f"Config label '{config_label}' contained in TSX label '{tsx_label}'"
                    ))
                    continue
            
            # Rule 6: Label contained by (tsx label stripped in config label)
            if tsx_label_stripped and len(tsx_label_stripped) >= 3 and tsx_label_stripped in config_label:
                candidates.append((
                    config_field,
                    MatchConfidence.LABEL_CONTAINED_BY,
                    f"TSX label '{tsx_label_stripped}' contained in config label '{config_label}'"
                ))
                continue
            
            # Rule 7: Word-start match using abbreviations ONLY
            # Only triggers when tsx first word is a known abbreviation in config
            if tsx_label_stripped and config_label:
                tsx_words = tsx_label_stripped.split()
                config_words = config_label.split()
                tsx_first_word = tsx_words[0] if tsx_words else ''
                config_first_word = config_words[0] if config_words else ''
                
                if tsx_first_word and config_first_word:
                    # Only check if tsx word is a KNOWN abbreviation (must be in abbreviations dict)
                    abbreviations = self.matching_config.get('abbreviations', {})
                    
                    if tsx_first_word in abbreviations:
                        tsx_expanded = abbreviations[tsx_first_word]
                        
                        if config_first_word.startswith(tsx_expanded):
                            candidates.append((
                                config_field,
                                MatchConfidence.WORD_START_MATCH,
                                f"Abbreviation match: '{tsx_first_word}' -> '{config_first_word}' (expanded: '{tsx_expanded}')"
                            ))
                            continue
            
            # Rule 8: Synonym match from config
            synonyms = self.matching_config.get('label_synonyms', {})
            matched_synonym = False
            for base_label, synonym_list in synonyms.items():
                # Check if config matches base or synonyms
                config_matches = (config_label == base_label or config_label in synonym_list)
                # Check if tsx matches base or synonyms
                tsx_matches = (tsx_label_stripped == base_label or tsx_label_stripped in synonym_list or
                               tsx_label == base_label or tsx_label in synonym_list)
                
                if config_matches and tsx_matches:
                    candidates.append((
                        config_field,
                        MatchConfidence.SYNONYM_MATCH,
                        f"Synonym match: '{tsx_label}' <-> '{config_label}' (base: '{base_label}')"
                    ))
                    matched_synonym = True
                    break
            
            if matched_synonym:
                continue
        
        if candidates:
            # Sort by confidence (lower enum value = higher confidence)
            candidates.sort(key=lambda x: x[1].value)
            return candidates[0]
        
        return None
    def _normalize_field_id(self, field_id: str) -> str:
        """Normalize field ID for comparison."""
        if not field_id:
            return ''
        
        result = field_id.lower()
        
        # Remove common prefixes
        prefixes = ['new', 'edit', 'update', 'filter', 'search', 'input', 'field', 'txt', 'sel']
        for prefix in prefixes:
            if result.startswith(prefix) and len(result) > len(prefix):
                next_char_idx = len(prefix)
                if next_char_idx < len(result):
                    next_char = result[next_char_idx]
                    if next_char.isupper() or next_char == '_' or next_char.isupper():
                        result = result[next_char_idx:]
                        break
        
        # Remove separators
        result = re.sub(r'[_\-\s]', '', result)
        
        return result
    
    def _map_handlers(
        self,
        tsx_handlers: List[Dict],
        screen_layout: Dict,
        story_id: str
    ) -> Tuple[List[HandlerMapping], List[Dict]]:
        """Map TSX handlers to config actions."""
        mappings = []
        unmapped = []
        
        # Extract button actions from config
        config_buttons = []
        for section in screen_layout.get('layout_sections', []):
            for field in section.get('fields', []):
                if field.get('type') == 'button':
                    config_buttons.append(field)
        
        # Get APIs for this story
        story_apis = screen_layout.get('apis', [])
        
        for tsx_handler in tsx_handlers:
            # Skip stub handlers (inline showNotification calls)
            if tsx_handler.get('is_stub', False):
                continue
            
            match = self._find_handler_match(tsx_handler, config_buttons, story_apis)
            
            if match:
                config_button, api_info = match
                
                mappings.append(HandlerMapping(
                    tsx_function_name=tsx_handler['function_name'],
                    tsx_button_text=tsx_handler.get('button_text'),
                    story_id=story_id,
                    config_action=config_button.get('events', {}).get('onClick', ''),
                    target_api_endpoint=api_info.get('endpoint', ''),
                    target_api_method=api_info.get('method', 'POST'),
                    target_entity=api_info.get('entity', ''),
                    confidence='HIGH',
                    match_reason=f"Button text match: '{tsx_handler.get('button_text')}'"
                ))
            else:
                unmapped.append({
                    'function_name': tsx_handler['function_name'],
                    'button_text': tsx_handler.get('button_text'),
                    'reason': 'no_config_match'
                })
        
        return mappings, unmapped
    
    def _find_handler_match(
        self,
        tsx_handler: Dict,
        config_buttons: List[Dict],
        story_apis: List[Dict]
    ) -> Optional[Tuple[Dict, Dict]]:
        """Find matching config button and API for handler."""
        
        tsx_button_text = (tsx_handler.get('button_text') or '').lower()
        tsx_button_normalized = self._normalize_text(tsx_button_text)
        tsx_function_normalized = self._normalize_text(tsx_handler.get('function_name', ''))
        
        for config_button in config_buttons:
            config_label = config_button.get('label', '').lower()
            config_label_normalized = self._normalize_text(config_label)
            config_id_normalized = self._normalize_text(config_button.get('id', ''))
            
            # Match by button label
            if tsx_button_normalized == config_label_normalized:
                api = self._find_api_for_button(config_button, story_apis)
                return config_button, api or {}
            
            # Match by function name to config ID
            if tsx_function_normalized == config_id_normalized:
                api = self._find_api_for_button(config_button, story_apis)
                return config_button, api or {}
            
            # Match by function name to config label
            if tsx_function_normalized == config_label_normalized:
                api = self._find_api_for_button(config_button, story_apis)
                return config_button, api or {}
        
        return None
    
    def _find_api_for_button(
        self,
        config_button: Dict,
        story_apis: List[Dict]
    ) -> Optional[Dict]:
        """Find the API that should be called for a button action."""
        
        # Determine action type from button events or ID
        action = config_button.get('events', {}).get('onClick', '')
        button_id = config_button.get('id', '')
        
        # Map action names to HTTP methods
        action_to_method = {
            'create': 'POST',
            'add': 'POST',
            'save': 'POST',
            'update': 'PUT',
            'edit': 'PUT',
            'change': 'PUT',
            'delete': 'DELETE',
            'remove': 'DELETE',
            'reverse': 'PUT',
            'start': 'POST',
        }
        
        # Determine expected method
        expected_method = None
        for keyword, method in action_to_method.items():
            if keyword in action.lower() or keyword in button_id.lower():
                expected_method = method
                break
        
        if not expected_method:
            expected_method = 'POST'  # Default to POST for actions
        
        # Find matching API
        for api in story_apis:
            if api.get('method') == expected_method:
                return api
        
        # Fallback: return first POST API
        for api in story_apis:
            if api.get('method') == 'POST':
                return api
        
        return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ''
        return re.sub(r'[^a-z0-9]', '', text.lower())
    
    def _map_top_level_handlers(
        self,
        top_level_handlers: List[Dict]
    ) -> List[Dict]:
        """Map top-level handlers to screen contexts."""
        mappings = []
        
        for handler in top_level_handlers:
            if handler.get('is_stub'):
                continue
            
            func_name = handler['function_name']
            
            # Find which screen uses this handler
            for screen in self.tsx_metadata.get('screens', []):
                for h in screen.get('handlers', []):
                    if h.get('function_name') == func_name:
                        mappings.append({
                            'function_name': func_name,
                            'used_in_screen': screen['component_name'],
                            'line_number': handler['line_number'],
                            'needs_wiring': True
                        })
                        break
        
        return mappings
    
    def _determine_primary_entity(self, screen_layout: Dict) -> str:
        """Determine the primary entity for a screen."""
        # Check for explicit primary_entity
        if 'primary_entity' in screen_layout:
            return screen_layout['primary_entity']
        
        # Look at field bindings
        entity_counts = {}
        for section in screen_layout.get('layout_sections', []):
            for field in section.get('fields', []):
                binding = field.get('binding', '')
                if '.' in binding:
                    entity = binding.split('.')[0]
                    entity_counts[entity] = entity_counts.get(entity, 0) + 1
        
        if entity_counts:
            return max(entity_counts, key=entity_counts.get)
        
        return 'nsi_items'  # This should come from config, not hardcoded
    
    def _get_field_validations(self, field_id: str, story_id: str) -> List[Dict]:
        """Get validation rules for a field."""
        validations = []
        
        for rule in self.validation_rules:
            if rule.get('field_id') == field_id and rule.get('story_id') == story_id:
                validations.append({
                    'rule': rule.get('rule'),
                    'error_message': rule.get('error_message'),
                    'field_type': rule.get('field_type'),
                    'required': rule.get('required', False)
                })
        
        return validations
    
    def _get_field_error_messages(self, field_id: str, story_id: str) -> Dict[str, str]:
        """Get error messages for a field."""
        messages = {}
        
        for msg in self.error_messages:
            if msg.get('field_id') == field_id and msg.get('story_id') == story_id:
                rule = msg.get('rule', '')
                message = msg.get('message', '')
                if rule and message:
                    messages[rule] = message
        
        return messages
    
    def _build_entity_services(self) -> List[Dict]:
        """Build service definitions for all entities."""
        services = []
        
        for entity_name, entity_def in self.entities.items():
            # Find APIs for this entity
            entity_apis = [
                api for api in self.config.get('apis', [])
                if api.get('entity') == entity_name
            ]
            
            services.append({
                'entity_name': entity_name,
                'service_name': self._to_pascal_case(entity_name) + 'Service',
                'primary_key': entity_def.get('primary_key', 'id'),
                'primary_key_type': entity_def.get('primary_key_type', 'int'),
                'fields': entity_def.get('fields', []),
                'apis': entity_apis
            })
        
        return services
    
    def _build_validation_summary(self) -> Dict[str, Any]:
        """Build summary of all validations."""
        return {
            'total_validation_rules': len(self.validation_rules),
            'total_error_messages': len(self.error_messages),
            'total_field_validations': len(self.field_validations),
            'stories_with_validations': list(set(
                v.get('story_id') for v in self.validation_rules if v.get('story_id')
            ))
        }
    
    def _build_ac_coverage_with_mapping(self, screen_mappings: List) -> Dict[str, Any]:
        """Build acceptance criteria coverage enhanced with field mapping status."""
        
        # Start with Step 06 coverage if available
        coverage = {}
        
        # Build set of mapped config field IDs per story
        mapped_fields_by_story = {}
        for sm in screen_mappings:
            story_id = sm.story_id
            if story_id not in mapped_fields_by_story:
                mapped_fields_by_story[story_id] = set()
            for fm in sm.field_mappings:
                mapped_fields_by_story[story_id].add(fm.config_field_id)
                mapped_fields_by_story[story_id].add(fm.config_label.lower())
        
        # Process each story's acceptance criteria
        for story_id, acs in self.ac_by_story.items():
            story_coverage = {}
            mapped_fields = mapped_fields_by_story.get(story_id, set())
            
            # Get required fields for this story from screen_layouts
            story_required_fields = []
            for layout in self.screen_layouts:
                if layout.get('story_id') == story_id:
                    for section in layout.get('layout_sections', []):
                        for field in section.get('fields', []):
                            story_required_fields.append({
                                'id': field.get('id', ''),
                                'label': field.get('label', '')
                            })
            
            for ac in acs:
                ac_id = ac.get('id', '')
                ac_title = ac.get('title', '')
                
                # Check field coverage with mapping status
                fields_in_tsx = []
                fields_mapped = []
                fields_missing = []
                
                for field in story_required_fields:
                    field_id = field.get('id', '').lower()
                    field_label = field.get('label', '').lower()
                    
                    # Check if in TSX (from Step 06 coverage)
                    step06_coverage = self.ac_coverage_from_step06.get(story_id, {}).get(ac_id, {})
                    found_fields = [f.lower() for f in step06_coverage.get('found_fields', [])]
                    
                    in_tsx = field_label in found_fields or field_id in found_fields
                    is_mapped = field_id in mapped_fields or field_label in mapped_fields
                    
                    field_info = field.get('label') or field.get('id')
                    
                    if in_tsx:
                        fields_in_tsx.append(field_info)
                        if is_mapped:
                            fields_mapped.append(field_info)
                        else:
                            # In TSX but not mapped (wiring issue)
                            fields_missing.append(f"{field_info} (in TSX, not mapped)")
                    else:
                        # Not in TSX at all
                        fields_missing.append(f"{field_info} (not in TSX)")
                
                total = len(story_required_fields)
                mapped_count = len(fields_mapped)
                coverage_pct = round((mapped_count / total * 100) if total > 0 else 100)
                
                story_coverage[ac_id] = {
                    'title': ac_title,
                    'total_required_fields': total,
                    'fields_in_tsx': len(fields_in_tsx),
                    'fields_mapped': mapped_count,
                    'fields_missing': len(fields_missing),
                    'coverage_percent': coverage_pct,
                    'mapped_field_list': fields_mapped,
                    'missing_field_list': fields_missing,
                    'status': 'COMPLETE' if coverage_pct == 100 else 'INCOMPLETE'
                }
            
            if story_coverage:
                coverage[story_id] = story_coverage
        
        return coverage
    
    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase."""
        return ''.join(word.capitalize() for word in re.split(r'[^a-zA-Z0-9]+', name) if word)


def main():
    """Main entry point."""
    if len(sys.argv) < 4:
        print("Usage: python step_07_frontend_wiring_gemini_llm.py <app_config.json> <tsx_metadata.json> <output_wired_ui.json>")
        sys.exit(1)
    
    app_config_path = Path(sys.argv[1])
    tsx_metadata_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    
    print(f"--- Step 07: Frontend Wiring Plan Generation (v2.0-deterministic) ---")
    print(f"App Config: {app_config_path}")
    print(f"TSX Metadata: {tsx_metadata_path}")
    print(f"Output: {output_path}")
    
    # Load inputs
    with open(app_config_path, 'r', encoding='utf-8') as f:
        app_config = json.load(f)
    
    with open(tsx_metadata_path, 'r', encoding='utf-8') as f:
        tsx_metadata = json.load(f)
    
    # Generate wiring plan
    planner = WiringPlanner(app_config, tsx_metadata)
    wiring_plan = planner.generate_wiring_plan()
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(wiring_plan, f, indent=2)
    
    # Print summary
    print(f"\n[SUCCESS] Wiring plan generated:")
    print(f"  - Screen mappings: {len(wiring_plan['screen_mappings'])}")
    print(f"  - Entity services: {len(wiring_plan['entity_services'])}")
    print(f"  - Mock data to remove: {len(wiring_plan['mock_data_removal'])}")
    print(f"  - Unmapped fields: {len(wiring_plan['unmapped_elements']['fields'])}")
    print(f"  - Unmapped handlers: {len(wiring_plan['unmapped_elements']['handlers'])}")
    
    for sm in wiring_plan['screen_mappings']:
        print(f"\n  Screen: {sm['tsx_screen_name']} -> {sm['story_id']}")
        print(f"    - Field mappings: {len(sm['field_mappings'])}")
        print(f"    - Handler mappings: {len(sm['handler_mappings'])}")
    
    # Print AC coverage summary
    ac_coverage = wiring_plan.get('acceptance_criteria_coverage', {})
    if ac_coverage:
        print(f"\n  --- Acceptance Criteria Coverage (with Mapping) ---")
        for story_id, story_coverage in ac_coverage.items():
            print(f"\n  {story_id}:")
            for ac_id, ac_data in story_coverage.items():
                coverage_pct = ac_data.get('coverage_percent', 0)
                status = "[OK]" if ac_data.get('status') == 'COMPLETE' else "[!!]"
                print(f"    {status} {ac_id}: {ac_data.get('title', '')} - {coverage_pct}% mapped")
                if ac_data.get('missing_field_list'):
                    missing = ac_data['missing_field_list'][:3]
                    print(f"      Missing: {', '.join(missing)}")
                    if len(ac_data['missing_field_list']) > 3:
                        print(f"      ... and {len(ac_data['missing_field_list']) - 3} more")


if __name__ == '__main__':
    main()
