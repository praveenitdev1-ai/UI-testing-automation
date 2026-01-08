import re
import json
import sys
import argparse
import os
import copy
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field as dataclass_field
from enum import Enum
from dotenv import load_dotenv
import openai
from step_1b_rag_enhanced_analyzer import create_rag_enhanced_analyzer, RAGEnhancedUIAnalyzer

# Azure Key Vault imports
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ClientAuthenticationError


# --- Azure CLI Path Configuration ---
def _ensure_azure_cli_available():
    """Ensure Azure CLI is available and add to PATH if needed"""
    import subprocess
    
    # Check if 'az' command is available in current PATH
    try:
        subprocess.run(['az', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # If not available, check AZURE_CLI_PATH environment variable
    azure_cli_path = os.environ.get('AZURE_CLI_PATH')
    if azure_cli_path:
        if os.path.exists(azure_cli_path):
            # Add to PATH for this session
            current_path = os.environ.get('PATH', '')
            if azure_cli_path not in current_path:
                os.environ['PATH'] = azure_cli_path + os.pathsep + current_path
            
            # Test again after adding to PATH
            for az_command in ['az', 'az.cmd', 'az.exe']:
                try:
                    subprocess.run([az_command, '--version'], capture_output=True, check=True)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
    
    # Try common Azure CLI installation paths as fallback
    common_paths = [
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin",
        r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            for az_file in ['az.cmd', 'az.exe']:
                az_full_path = os.path.join(path, az_file)
                if os.path.exists(az_full_path):
                    current_path = os.environ.get('PATH', '')
                    if path not in current_path:
                        os.environ['PATH'] = path + os.pathsep + current_path
                    
                    try:
                        subprocess.run([az_file, '--version'], capture_output=True, check=True)
                        return True
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
    
    return False


# --- Azure Key Vault functions ---
def get_azure_openai_api_key_from_keyvault():
    """Get the Azure OpenAI API key from Azure Key Vault"""
    keyvault_url = "https://kv-sdlc-pipeline.vault.azure.net/"
    secret_name = "GPT41"
    
    print("Azure Authentication Details:")
    
    # Ensure Azure CLI is available before attempting authentication
    if not _ensure_azure_cli_available():
        print("Azure CLI not available - cannot authenticate with Key Vault")
        print("Authentication Method: None (Azure CLI required)")
        print("Fallback: Using .env file for API key")
        return None
    
    try:
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=keyvault_url, credential=credential)
        
        # Get the API key from Key Vault
        print("Attempting to retrieve secret from Key Vault...")
        secret = client.get_secret(secret_name)
        
        print("Successfully authenticated with Azure Key Vault")
        print("API Key Source: Azure Key Vault")
        
        return secret.value
        
    except ClientAuthenticationError as e:
        print(f"Key Vault authentication failed: {str(e)}")
        print("Fallback: Using .env file for API key")
        return None
    except Exception as e:
        print(f"Key Vault error: {str(e)}")
        print("Fallback: Using .env file for API key")
        return None


class ElementType(Enum):
    INPUT = "input"
    SELECT = "select"
    BUTTON = "button"
    TABLE = "table"
    GRID = "grid"
    DIV = "div"
    LABEL = "label"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"
    SPAN = "span"


@dataclass
class ValidationRule:
    type: str
    message: Optional[str] = None
    condition: Optional[str] = None


@dataclass
class ElementAction:
    event: str
    handler: str
    description: Optional[str] = None


@dataclass
class UIElement:
    element_type: str
    attributes: Dict[str, Any] = dataclass_field(default_factory=dict)
    validations: List[ValidationRule] = dataclass_field(default_factory=list)
    actions: List[ElementAction] = dataclass_field(default_factory=list)
    children: List['UIElement'] = dataclass_field(default_factory=list)
    text_content: Optional[str] = None
    label: Optional[str] = None
    placeholder: Optional[str] = None


@dataclass
class Screen:
    name: str
    component_name: str
    description: Optional[str] = None
    elements: List[UIElement] = dataclass_field(default_factory=list)
    state_variables: List[Dict[str, Any]] = dataclass_field(default_factory=list)
    functions: List[Dict[str, Any]] = dataclass_field(default_factory=list)


@dataclass
class ReactComponentAnalysis:
    component_name: str
    file_path: Optional[str] = None
    screens: List[Screen] = dataclass_field(default_factory=list)
    global_state: List[Dict[str, Any]] = dataclass_field(default_factory=list)
    global_functions: List[Dict[str, Any]] = dataclass_field(default_factory=list)


class ReactComponentParser:
    def __init__(self):
        self.current_analysis = None
        
    def parse_file(self, file_path: str) -> ReactComponentAnalysis:
        """Parse a React/TSX or HTML file and extract all details"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Detect file type
        file_extension = Path(file_path).suffix.lower()
        
        return self.parse_content(content, file_path, file_extension)
    
    def parse_content(self, content: str, file_path: Optional[str] = None, file_extension: str = '.tsx') -> ReactComponentAnalysis:
        """Parse React component or HTML content"""
        # Extract component name
        component_name = self._extract_component_name(content, file_extension)
        
        self.current_analysis = ReactComponentAnalysis(
            component_name=component_name,
            file_path=file_path
        )
        
        # For HTML files, skip React-specific extractions
        if file_extension in ['.html', '.htm']:
            # HTML-specific parsing
            self.current_analysis.global_state = []  # No state in static HTML
            self.current_analysis.global_functions = self._extract_javascript_functions(content)
            self.current_analysis.screens = self._extract_html_screens(content)
        else:
            # React/TSX parsing (original behavior)
            self.current_analysis.global_state = self._extract_state_variables(content)
            self.current_analysis.global_functions = self._extract_functions(content)
            self.current_analysis.screens = self._extract_screens(content)
        
        return self.current_analysis
    
    def _extract_component_name(self, content: str, file_extension: str = '.tsx') -> str:
        """Extract the main component name"""
        
        if file_extension in ['.html', '.htm']:
            # For HTML files, extract from title or filename reference
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
            if title_match:
                return title_match.group(1).strip()
            
            # Look for main page identifier
            h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content, re.IGNORECASE)
            if h1_match:
                return h1_match.group(1).strip()
            
            return "HTML_Page"
        
        # React/TSX component patterns (original behavior)
        patterns = [
            r'const\s+(\w+)\s*=\s*\(\)',
            r'function\s+(\w+)\s*\(',
            r'export\s+default\s+(\w+)',
            r'const\s+(\w+):\s*React\.FC'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return "UnknownComponent"
    
    def _extract_state_variables(self, content: str) -> List[Dict[str, Any]]:
        """Extract useState declarations"""
        state_vars = []
        
        # Pattern for useState
        pattern = r'const\s+\[(\w+),\s*(\w+)\]\s*=\s*useState(?:<[^>]+>)?\(([^)]*)\)'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            state_name = match.group(1)
            setter_name = match.group(2)
            initial_value = match.group(3).strip()
            
            state_vars.append({
                'name': state_name,
                'setter': setter_name,
                'initial_value': initial_value,
                'type': self._infer_type(initial_value)
            })
        
        return state_vars
    
    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions"""
        functions = []
        
        # Pattern for function declarations
        patterns = [
            r'const\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>\s*\{',
            r'function\s+(\w+)\s*\(([^)]*)\)\s*\{'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                func_name = match.group(1)
                params = match.group(2).strip()
                
                # Extract function body
                func_body = self._extract_function_body(content, match.end())
                
                functions.append({
                    'name': func_name,
                    'parameters': params,
                    'body_preview': func_body[:200] if func_body else '',
                    'has_validation': 'if' in func_body and ('!' in func_body or 'return' in func_body),
                    'calls_notification': 'showNotification' in func_body,
                    'calls_modal': 'showModal' in func_body
                })
        
        return functions
    
    def _extract_javascript_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract JavaScript functions from HTML <script> tags"""
        functions = []
        
        # Find script tags
        script_pattern = r'<script[^>]*>(.*?)</script>'
        script_matches = re.finditer(script_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for script_match in script_matches:
            script_content = script_match.group(1)
            
            # Extract function declarations from JavaScript
            js_patterns = [
                r'function\s+(\w+)\s*\(([^)]*)\)\s*\{',
                r'const\s+(\w+)\s*=\s*function\s*\(([^)]*)\)\s*\{',
                r'(\w+)\s*:\s*function\s*\(([^)]*)\)\s*\{'
            ]
            
            for pattern in js_patterns:
                matches = re.finditer(pattern, script_content)
                for match in matches:
                    func_name = match.group(1)
                    params = match.group(2).strip() if len(match.groups()) > 1 else ''
                    
                    functions.append({
                        'name': func_name,
                        'parameters': params,
                        'body_preview': script_content[match.end():match.end()+200],
                        'type': 'javascript'
                    })
        
        return functions
    
    def _extract_html_screens(self, content: str) -> List[Screen]:
        """Extract screens/sections from HTML content"""
        screens = []
        
        # Look for main content sections
        section_patterns = [
            r'<section[^>]*>(.*?)</section>',
            r'<div[^>]*class="[^"]*page[^"]*"[^>]*>(.*?)</div>',
            r'<main[^>]*>(.*?)</main>',
            r'<article[^>]*>(.*?)</article>'
        ]
        
        screen_found = False
        
        for pattern in section_patterns:
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            for i, match in enumerate(matches):
                section_content = match.group(1)
                
                # Extract section name
                section_name = f"Section_{i+1}"
                
                # Try to find a heading for better naming
                heading_match = re.search(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', section_content, re.IGNORECASE)
                if heading_match:
                    section_name = heading_match.group(1).strip().replace(' ', '_')
                
                screen = Screen(
                    name=section_name,
                    component_name=section_name,
                    description=self._extract_section_description(section_content)
                )
                
                # Extract elements from section
                screen.elements = self._extract_html_elements(section_content)
                
                screens.append(screen)
                screen_found = True
        
        # If no sections found, treat entire body as one screen
        if not screen_found:
            body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
            if body_match:
                body_content = body_match.group(1)
            else:
                body_content = content
            
            screen = Screen(
                name="Main_Page",
                component_name="Main_Page",
                description=self._extract_section_description(body_content)
            )
            
            screen.elements = self._extract_html_elements(body_content)
            screens.append(screen)
        
        return screens
    
    def _extract_section_description(self, section_content: str) -> Optional[str]:
        """Extract description from HTML section"""
        # Look for headings
        patterns = [
            r'<h1[^>]*>([^<]+)</h1>',
            r'<h2[^>]*>([^<]+)</h2>',
            r'<h3[^>]*>([^<]+)</h3>',
            r'<p[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</p>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, section_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_html_elements(self, content: str) -> List[UIElement]:
        """Extract UI elements from HTML content (modified for HTML syntax)"""
        elements = []
        
        # Extract HTML inputs (modified patterns for HTML)
        elements.extend(self._extract_html_inputs(content))
        
        # Extract HTML selects
        elements.extend(self._extract_html_selects(content))
        
        # Extract HTML buttons
        elements.extend(self._extract_html_buttons(content))
        
        # Extract HTML tables
        elements.extend(self._extract_tables(content))  # Can reuse existing method
        
        # Extract HTML forms
        elements.extend(self._extract_html_forms(content))
        
        return elements
    
    def _extract_html_inputs(self, content: str) -> List[UIElement]:
        """Extract HTML input elements (handles standard HTML attributes)"""
        inputs = []
        pattern = r'<input\s+([^>]+)/?>'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            attrs_str = match.group(1)
            attrs = self._parse_html_attributes(attrs_str)
            
            # Extract HTML event handlers
            actions = self._extract_html_element_actions(attrs)
            
            # Find associated label (look for label with for attribute or wrapping label)
            label = self._find_html_label_for_input(content, match.start(), attrs.get('id', ''))
            
            element = UIElement(
                element_type=ElementType.INPUT.value,
                attributes=attrs,
                actions=actions,
                label=label,
                placeholder=attrs.get('placeholder')
            )
            
            inputs.append(element)
        
        return inputs
    
    def _extract_html_selects(self, content: str) -> List[UIElement]:
        """Extract HTML select elements"""
        selects = []
        pattern = r'<select\s+([^>]+)>(.*?)</select>'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            attrs_str = match.group(1)
            options_content = match.group(2)
            attrs = self._parse_html_attributes(attrs_str)
            
            # Extract options
            options = self._extract_options(options_content)
            attrs['options'] = options
            
            # Extract actions
            actions = self._extract_html_element_actions(attrs)
            
            # Find associated label
            label = self._find_html_label_for_input(content, match.start(), attrs.get('id', ''))
            
            element = UIElement(
                element_type=ElementType.SELECT.value,
                attributes=attrs,
                actions=actions,
                label=label
            )
            
            selects.append(element)
        
        return selects
    
    def _extract_html_buttons(self, content: str) -> List[UIElement]:
        """Extract HTML button elements"""
        buttons = []
        
        # Button tags
        button_pattern = r'<button\s+([^>]*)>([^<]*)</button>'
        matches = re.finditer(button_pattern, content)
        
        for match in matches:
            attrs_str = match.group(1)
            text = match.group(2).strip()
            attrs = self._parse_html_attributes(attrs_str)
            
            actions = self._extract_html_element_actions(attrs)
            
            element = UIElement(
                element_type=ElementType.BUTTON.value,
                attributes=attrs,
                actions=actions,
                text_content=text
            )
            
            buttons.append(element)
        
        # Input buttons
        input_button_pattern = r'<input\s+type=["\'](button|submit|reset)["\']([^>]*)/?>'
        matches = re.finditer(input_button_pattern, content)
        
        for match in matches:
            button_type = match.group(1)
            attrs_str = match.group(2)
            attrs = self._parse_html_attributes(f'type="{button_type}" {attrs_str}')
            
            actions = self._extract_html_element_actions(attrs)
            
            element = UIElement(
                element_type=ElementType.BUTTON.value,
                attributes=attrs,
                actions=actions,
                text_content=attrs.get('value', f'{button_type.title()} Button')
            )
            
            buttons.append(element)
        
        return buttons
    
    def _extract_html_forms(self, content: str) -> List[UIElement]:
        """Extract HTML form elements"""
        forms = []
        pattern = r'<form\s+([^>]*)>(.*?)</form>'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            attrs_str = match.group(1)
            form_content = match.group(2)
            attrs = self._parse_html_attributes(attrs_str)
            
            # Count form elements inside
            input_count = len(re.findall(r'<input', form_content))
            select_count = len(re.findall(r'<select', form_content))
            textarea_count = len(re.findall(r'<textarea', form_content))
            
            attrs['form_elements'] = {
                'inputs': input_count,
                'selects': select_count,
                'textareas': textarea_count,
                'total': input_count + select_count + textarea_count
            }
            
            element = UIElement(
                element_type='form',
                attributes=attrs
            )
            
            forms.append(element)
        
        return forms
    
    def _parse_html_attributes(self, attrs_str: str) -> Dict[str, Any]:
        """Parse HTML attributes (handles standard HTML syntax)"""
        attrs = {}
        
        # Pattern for attribute="value" or attribute='value'
        pattern = r'(\w+)=["\']([^"\']*)["\']'
        matches = re.finditer(pattern, attrs_str)
        
        for match in matches:
            key = match.group(1)
            value = match.group(2)
            attrs[key] = value
        
        # Handle boolean attributes (like checked, disabled)
        boolean_attrs = ['checked', 'disabled', 'readonly', 'required', 'multiple']
        for attr in boolean_attrs:
            if re.search(rf'\b{attr}\b', attrs_str):
                attrs[attr] = True
        
        return attrs
    
    def _extract_html_element_actions(self, attrs: Dict[str, Any]) -> List[ElementAction]:
        """Extract HTML event handlers from attributes"""
        actions = []
        
        html_event_handlers = {
            'onclick': 'click',
            'onchange': 'change',
            'onsubmit': 'submit',
            'onfocus': 'focus',
            'onblur': 'blur',
            'onkeypress': 'keypress',
            'onkeydown': 'keydown',
            'onmouseover': 'mouseover',
            'onmouseout': 'mouseout'
        }
        
        for attr_key, event_type in html_event_handlers.items():
            if attr_key in attrs:
                handler = attrs[attr_key]
                
                description = self._extract_action_description(handler)
                
                action = ElementAction(
                    event=event_type,
                    handler=handler,
                    description=description
                )
                actions.append(action)
        
        return actions
    
    def _find_html_label_for_input(self, content: str, input_pos: int, input_id: str) -> Optional[str]:
        """Find HTML label for input element"""
        
        # Method 1: Look for <label for="input_id">
        if input_id:
            label_pattern = rf'<label[^>]*for=["\']?{input_id}["\']?[^>]*>([^<]+)</label>'
            match = re.search(label_pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Method 2: Look for wrapping label
        search_start = max(0, input_pos - 300)
        search_end = min(len(content), input_pos + 100)
        search_content = content[search_start:search_end]
        
        # Find if input is inside a label
        label_wrap_pattern = r'<label[^>]*>([^<]*)<input'
        match = re.search(label_wrap_pattern, search_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Method 3: Look backwards for closest label
        search_back = content[max(0, input_pos - 200):input_pos]
        label_pattern = r'<label[^>]*>([^<]+)</label>'
        matches = list(re.finditer(label_pattern, search_back, re.IGNORECASE))
        
        if matches:
            return matches[-1].group(1).strip()
        
        return None
    
    def _extract_function_body(self, content: str, start_pos: int) -> str:
        """Extract function body using brace matching"""
        brace_count = 1
        pos = start_pos
        body = []
        
        while pos < len(content) and brace_count > 0:
            char = content[pos]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            
            if brace_count > 0:
                body.append(char)
            pos += 1
        
        return ''.join(body)
    
    def _extract_screens(self, content: str) -> List[Screen]:
        """Extract screen components"""
        screens = []
        
        # Pattern for screen component declarations
        pattern = r'const\s+(\w+Screen|\w+View)\s*=\s*\(\)\s*=>\s*\('
        matches = re.finditer(pattern, content)
        
        for match in matches:
            screen_name = match.group(1)
            screen_content = self._extract_component_content(content, match.end())
            
            screen = Screen(
                name=screen_name,
                component_name=screen_name,
                description=self._extract_screen_description(screen_content)
            )
            
            # Extract elements from screen
            screen.elements = self._extract_elements(screen_content)
            
            screens.append(screen)
        
        return screens
    
    def _extract_component_content(self, content: str, start_pos: int) -> str:
        """Extract component JSX content"""
        paren_count = 1
        pos = start_pos
        component_content = []
        
        while pos < len(content) and paren_count > 0:
            char = content[pos]
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            
            if paren_count > 0:
                component_content.append(char)
            pos += 1
        
        return ''.join(component_content)
    
    def _extract_screen_description(self, screen_content: str) -> Optional[str]:
        """Extract screen description from h1, h2, or title elements"""
        patterns = [
            r'<h1[^>]*>([^<]+)</h1>',
            r'<h2[^>]*>([^<]+)</h2>',
            r'<h3[^>]*>([^<]+)</h3>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, screen_content)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_elements(self, content: str) -> List[UIElement]:
        """Extract all UI elements from content"""
        elements = []
        
        # Extract inputs
        elements.extend(self._extract_inputs(content))
        
        # Extract selects
        elements.extend(self._extract_selects(content))
        
        # Extract buttons
        elements.extend(self._extract_buttons(content))
        
        # Extract tables
        elements.extend(self._extract_tables(content))
        
        # Extract CSS grids
        elements.extend(self._extract_grids(content))
        
        # Extract checkboxes
        elements.extend(self._extract_checkboxes(content))
        
        return elements
    
    def _extract_inputs(self, content: str) -> List[UIElement]:
        """Extract input elements"""
        inputs = []
        pattern = r'<input\s+([^>]+)/?>'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            attrs_str = match.group(1)
            attrs = self._parse_attributes(attrs_str)
            
            # Extract validation from id reference
            validations = self._extract_input_validations(content, attrs.get('id', ''))
            
            # Extract actions
            actions = self._extract_element_actions(attrs)
            
            # Find associated label
            label = self._find_label_for_input(content, match.start())
            
            element = UIElement(
                element_type=ElementType.INPUT.value,
                attributes=attrs,
                validations=validations,
                actions=actions,
                label=label,
                placeholder=attrs.get('placeholder')
            )
            
            inputs.append(element)
        
        return inputs
    
    def _extract_selects(self, content: str) -> List[UIElement]:
        """Extract select elements"""
        selects = []
        pattern = r'<select\s+([^>]+)>(.*?)</select>'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            attrs_str = match.group(1)
            options_content = match.group(2)
            attrs = self._parse_attributes(attrs_str)
            
            # Extract options
            options = self._extract_options(options_content)
            attrs['options'] = options
            
            # Extract actions
            actions = self._extract_element_actions(attrs)
            
            # Find associated label
            label = self._find_label_for_input(content, match.start())
            
            element = UIElement(
                element_type=ElementType.SELECT.value,
                attributes=attrs,
                actions=actions,
                label=label
            )
            
            selects.append(element)
        
        return selects
    
    def _extract_buttons(self, content: str) -> List[UIElement]:
        """Extract button elements"""
        buttons = []
        pattern = r'<button\s+([^>]+)>([^<]*)</button>'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            attrs_str = match.group(1)
            text = match.group(2).strip()
            attrs = self._parse_attributes(attrs_str)
            
            # Extract actions
            actions = self._extract_element_actions(attrs)
            
            element = UIElement(
                element_type=ElementType.BUTTON.value,
                attributes=attrs,
                actions=actions,
                text_content=text
            )
            
            buttons.append(element)
        
        return buttons
    
    def _extract_tables(self, content: str) -> List[UIElement]:
        """Extract table elements with headers and sample data"""
        tables = []
        pattern = r'<table\s+([^>]*)>(.*?)</table>'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            attrs_str = match.group(1)
            table_content = match.group(2)
            attrs = self._parse_attributes(attrs_str)
            
            # Extract headers
            headers = self._extract_table_headers(table_content)
            attrs['headers'] = headers
            
            # Count rows
            row_pattern = r'<tr[^>]*>.*?</tr>'
            rows = re.findall(row_pattern, table_content, re.DOTALL)
            attrs['row_count'] = len(rows)
            
            element = UIElement(
                element_type=ElementType.TABLE.value,
                attributes=attrs
            )
            
            tables.append(element)
        
        return tables
    
    def _extract_grids(self, content: str) -> List[UIElement]:
        """Extract CSS Grid layouts from div elements with display: grid"""
        grids = []
        
        # Pattern to match div elements with style containing display: 'grid'
        # This captures both inline styles and JSX-style objects
        grid_patterns = [
            # JSX style objects: style={{ display: 'grid', ... }}
            r'<div\s+([^>]*style\s*=\s*\{\{\s*[^}]*display\s*:\s*[\'"]grid[\'"][^}]*\}\}[^>]*)>',
            # Inline CSS: style="display: grid; ..."
            r'<div\s+([^>]*style\s*=\s*[\'"][^\'\"]*display\s*:\s*grid[^\'\"]*[\'"][^>]*)>',
        ]
        
        for pattern in grid_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                attrs_str = match.group(1)
                
                # Extract grid-specific properties from the style
                grid_attrs = self._parse_grid_attributes(attrs_str)
                
                # Try to find a descriptive comment or label near the grid
                grid_description = self._find_grid_description(content, match.start())
                if grid_description:
                    grid_attrs['description'] = grid_description
                
                # Extract children elements within the grid
                grid_content = self._extract_grid_content(content, match.end())
                if grid_content:
                    grid_attrs['children_count'] = len(grid_content.get('children', []))
                    grid_attrs['grid_items'] = grid_content.get('children', [])
                
                element = UIElement(
                    element_type=ElementType.GRID.value,
                    attributes=grid_attrs,
                    text_content=grid_description
                )
                
                grids.append(element)
        
        return grids
    
    def _parse_grid_attributes(self, attrs_str: str) -> Dict[str, Any]:
        """Parse CSS Grid specific attributes from style string"""
        grid_attrs = {}
        
        # Parse general attributes first
        base_attrs = self._parse_attributes(attrs_str)
        grid_attrs.update(base_attrs)
        
        # Extract grid-specific CSS properties
        style_patterns = {
            'gridTemplateColumns': r'gridTemplateColumns\s*:\s*[\'"]([^\'\"]*)[\'"]',
            'gridTemplateRows': r'gridTemplateRows\s*:\s*[\'"]([^\'\"]*)[\'"]',
            'gap': r'gap\s*:\s*[\'"]([^\'\"]*)[\'"]',
            'gridGap': r'gridGap\s*:\s*[\'"]([^\'\"]*)[\'"]',
            'alignItems': r'alignItems\s*:\s*[\'"]([^\'\"]*)[\'"]',
            'justifyContent': r'justifyContent\s*:\s*[\'"]([^\'\"]*)[\'"]',
            'gridColumn': r'gridColumn\s*:\s*[\'"]([^\'\"]*)[\'"]',
        }
        
        for prop_name, pattern in style_patterns.items():
            match = re.search(pattern, attrs_str)
            if match:
                grid_attrs[prop_name] = match.group(1)
        
        # Try to determine number of columns from gridTemplateColumns
        if 'gridTemplateColumns' in grid_attrs:
            columns_def = grid_attrs['gridTemplateColumns']
            
            # Handle repeat() function: repeat(4, 1fr) -> 4 columns
            repeat_match = re.search(r'repeat\((\d+),', columns_def)
            if repeat_match:
                grid_attrs['estimated_columns'] = int(repeat_match.group(1))
            else:
                # Count space-separated values: '1fr 1fr 1fr auto auto' -> 5 columns
                column_count = len(columns_def.split())
                if column_count > 0:
                    grid_attrs['estimated_columns'] = column_count
        
        return grid_attrs
    
    def _extract_div_content(self, content: str, start_pos: int) -> Optional[str]:
        """Extract content between matching div opening and closing tags"""
        # Find the full opening div tag
        opening_tag_match = re.search(r'<div[^>]*>', content[start_pos:])
        if not opening_tag_match:
            return None
        
        opening_end = start_pos + opening_tag_match.end()
        
        # Find matching closing </div> tag
        div_count = 1
        pos = opening_end
        
        while pos < len(content) and div_count > 0:
            # Look for next opening or closing div tag
            next_opening = content.find('<div', pos)
            next_closing = content.find('</div>', pos)
            
            # If no closing tag found, return None
            if next_closing == -1:
                return None
            
            # If there's an opening div before the closing div, increment count
            if next_opening != -1 and next_opening < next_closing:
                div_count += 1
                pos = next_opening + 4  # Skip past '<div'
            else:
                div_count -= 1
                if div_count == 0:
                    # Found matching closing tag
                    return content[opening_end:next_closing]
                pos = next_closing + 6  # Skip past '</div>'
        
        return None
    
    def _find_grid_description(self, content: str, grid_position: int) -> Optional[str]:
        """Find descriptive comment or label for a grid layout"""
        # Look for comments before the grid (within 200 characters)
        search_start = max(0, grid_position - 200)
        search_content = content[search_start:grid_position]
        
        # Look for comments like {/* Stats Grid */}
        comment_match = re.search(r'\{\s*/\*\s*([^*]*)\*/', search_content)
        if comment_match:
            return comment_match.group(1).strip()
        
        # Look for HTML comments
        html_comment_match = re.search(r'<!--\s*([^-]*)\s*-->', search_content)
        if html_comment_match:
            return html_comment_match.group(1).strip()
        
        return None
    
    def _extract_grid_content(self, content: str, grid_start: int) -> Optional[Dict[str, Any]]:
        """Extract content structure within a grid div"""
        # Find the div tag start position
        div_start = content.rfind('<div', 0, grid_start)
        if div_start == -1:
            return None
            
        # Use the correct method to extract div content between matching tags
        div_content = self._extract_div_content(content, div_start)
        
        if not div_content:
            return None
        
        # Extract detailed grid items with enhanced content analysis
        grid_items = self._extract_detailed_grid_items(div_content)
        
        return {
            'children': grid_items,
            'total_content_length': len(div_content),
            'detailed_sections': [item for item in grid_items if item.get('section_title')]
        }
    
    def _extract_detailed_grid_items(self, div_content: str) -> List[Dict[str, Any]]:
        """Extract detailed information from grid items including sections, titles, and interactive elements"""
        grid_items = []
        
        # Pattern to match div elements (grid items) - non-greedy and handle nested divs properly
        child_pattern = r'<div\s+([^>]*?)>(.*?)</div>'
        
        # Find all top-level div children
        div_positions = []
        pos = 0
        while True:
            div_start = div_content.find('<div', pos)
            if div_start == -1:
                break
                
            # Extract this div's content using proper nesting
            item_content = self._extract_div_content(div_content, div_start)
            if item_content:
                # Find the attributes of this div
                div_match = re.search(r'<div\s+([^>]*?)>', div_content[div_start:])
                if div_match:
                    attrs_str = div_match.group(1)
                    
                    # Parse basic attributes
                    child_attrs = self._parse_attributes(attrs_str)
                    
                    # Extract detailed content from the grid item
                    item_details = self._analyze_grid_item_content(item_content)
                    
                    child_info = {
                        'type': 'grid_item',
                        'attributes': child_attrs,
                        'text_content': item_details.get('primary_text', ''),
                        'section_title': item_details.get('section_title'),
                        'interactive_elements': item_details.get('interactive_elements', []),
                        'has_buttons': item_details.get('has_buttons', False),
                        'has_links': item_details.get('has_links', False),
                        'numeric_values': item_details.get('numeric_values', []),
                        'full_content': item_content.strip()
                    }
                    
                    grid_items.append(child_info)
            
            # Move past this div
            closing_tag = div_content.find('</div>', div_start)
            if closing_tag == -1:
                break
            pos = closing_tag + 6
        
        return grid_items
    
    def _analyze_grid_item_content(self, content: str) -> Dict[str, Any]:
        """Analyze the content within a single grid item to extract detailed information"""
        details = {
            'primary_text': '',
            'section_title': None,
            'interactive_elements': [],
            'has_buttons': False,
            'has_links': False,
            'numeric_values': []
        }
        
        # Extract section titles (h1-h6, strong text, or text in specific patterns)
        title_patterns = [
            r'<h[1-6][^>]*>([^<]+)</h[1-6]>',  # HTML headers
            r'<strong[^>]*>([^<]+)</strong>',    # Strong text
            r'<b[^>]*>([^<]+)</b>',              # Bold text
            r'<span[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</span>',  # Title classes
            r'<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>',    # Title divs
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if len(title) > 0 and not details['section_title']:
                    details['section_title'] = title
                    break
        
        # Extract buttons
        button_pattern = r'<button[^>]*>(.*?)</button>'
        button_matches = re.finditer(button_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in button_matches:
            button_text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            if button_text:
                details['interactive_elements'].append({
                    'type': 'button',
                    'text': button_text
                })
                details['has_buttons'] = True
        
        # Extract links
        link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        link_matches = re.finditer(link_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in link_matches:
            href = match.group(1)
            link_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            if link_text:
                details['interactive_elements'].append({
                    'type': 'link',
                    'text': link_text,
                    'href': href
                })
                details['has_links'] = True
        
        # Extract numeric values (useful for stats and metrics)
        numeric_pattern = r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?[%$KMB]?)\b'
        numeric_matches = re.finditer(numeric_pattern, content)
        for match in numeric_matches:
            details['numeric_values'].append(match.group(1))
        
        # Extract primary text content (remove HTML tags)
        clean_text = re.sub(r'<[^>]+>', ' ', content)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        details['primary_text'] = clean_text
        
        # Generic section title detection - look for common dashboard/card patterns
        if not details['section_title'] and clean_text:
            # Try to identify section titles using common patterns
            title_candidates = []
            
            # Pattern 1: Short text at the beginning (likely a title)
            first_line = clean_text.split('\n')[0].strip() if '\n' in clean_text else clean_text
            first_words = first_line.split()[:5]  # First 5 words
            first_phrase = ' '.join(first_words).strip()
            
            if len(first_phrase) > 2 and len(first_phrase) < 50:
                title_candidates.append(first_phrase)
            
            # Pattern 2: Text before numbers (common in stat cards)
            number_match = re.search(r'(.+?)\s+(\d+[%$KMB]?)', clean_text)
            if number_match:
                potential_title = number_match.group(1).strip()
                if len(potential_title) > 2 and len(potential_title) < 50:
                    title_candidates.append(potential_title)
            
            # Pattern 3: Capitalized words that look like titles
            capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
            cap_matches = re.findall(capitalized_pattern, clean_text)
            for match in cap_matches:
                if len(match) > 5 and len(match) < 50 and match not in ['Click', 'View', 'Details']:
                    title_candidates.append(match)
            
            # Choose the best candidate (shortest reasonable length, typically the title)
            if title_candidates:
                best_candidate = min(title_candidates, key=len)
                if len(best_candidate) > 3:
                    details['section_title'] = best_candidate
        
        return details
    
    def _extract_component_content(self, content: str, start_pos: int) -> Optional[str]:
        """Extract content between matching opening and closing tags"""
        # Find the opening tag
        tag_match = re.search(r'<(\w+)', content[start_pos:])
        if not tag_match:
            return None
        
        tag_name = tag_match.group(1)
        
        # Find the full opening tag
        opening_tag_match = re.search(f'<{tag_name}[^>]*>', content[start_pos:])
        if not opening_tag_match:
            return None
        
        opening_end = start_pos + opening_tag_match.end()
        
        # Find matching closing tag
        tag_count = 1
        pos = opening_end
        
        while pos < len(content) and tag_count > 0:
            # Look for next opening or closing tag of the same type
            next_opening = content.find(f'<{tag_name}', pos)
            next_closing = content.find(f'</{tag_name}>', pos)
            
            # If no closing tag found, return None
            if next_closing == -1:
                return None
            
            # If there's an opening tag before the closing tag, increment count
            if next_opening != -1 and next_opening < next_closing:
                tag_count += 1
                pos = next_opening + 1
            else:
                tag_count -= 1
                if tag_count == 0:
                    # Found matching closing tag
                    return content[opening_end:next_closing]
                pos = next_closing + 1
        
        return None
    
    def _extract_checkboxes(self, content: str) -> List[UIElement]:
        """Extract checkbox inputs"""
        checkboxes = []
        pattern = r'<input\s+type=["\']checkbox["\']([^>]*)/?>'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            attrs_str = match.group(1)
            attrs = self._parse_attributes(f'type="checkbox" {attrs_str}')
            
            # Extract actions
            actions = self._extract_element_actions(attrs)
            
            element = UIElement(
                element_type=ElementType.CHECKBOX.value,
                attributes=attrs,
                actions=actions
            )
            
            checkboxes.append(element)
        
        return checkboxes
    
    def _parse_attributes(self, attrs_str: str) -> Dict[str, Any]:
        """Parse HTML attributes from string"""
        attrs = {}
        
        # Pattern for attribute="value" or attribute='value' or attribute={value}
        patterns = [
            r'(\w+)=["\']([^"\']*)["\']',
            r'(\w+)=\{([^}]*)\}'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, attrs_str)
            for match in matches:
                key = match.group(1)
                value = match.group(2)
                attrs[key] = value
        
        return attrs
    
    def _extract_element_actions(self, attrs: Dict[str, Any]) -> List[ElementAction]:
        """Extract event handlers from attributes"""
        actions = []
        
        event_handlers = {
            'onClick': 'click',
            'onChange': 'change',
            'onSubmit': 'submit',
            'onFocus': 'focus',
            'onBlur': 'blur',
            'onKeyPress': 'keypress',
            'onKeyDown': 'keydown'
        }
        
        for attr_key, event_type in event_handlers.items():
            if attr_key in attrs:
                handler = attrs[attr_key]
                
                # Try to extract description from handler
                description = self._extract_action_description(handler)
                
                action = ElementAction(
                    event=event_type,
                    handler=handler,
                    description=description
                )
                actions.append(action)
        
        return actions
    
    def _extract_action_description(self, handler: str) -> Optional[str]:
        """Extract description from action handler"""
        # Look for function calls
        function_calls = re.findall(r'(\w+)\(', handler)
        
        if function_calls:
            return f"Calls: {', '.join(function_calls)}"
        
        return None
    
    def _extract_input_validations(self, content: str, input_id: str) -> List[ValidationRule]:
        """Extract validations for an input field"""
        validations = []
        
        if not input_id:
            return validations
        
        # Look for validation logic referencing this input
        validation_patterns = [
            rf'if\s*\([^)]*getElementById\(["\']{input_id}["\'].*?\)',
            rf'if\s*\(!\s*{input_id}\)',
            rf'{input_id}\.value\s*===?\s*["\']',
        ]
        
        for pattern in validation_patterns:
            match = re.search(pattern, content)
            if match:
                validation_code = match.group(0)
                
                # Extract validation message
                message_match = re.search(r'showNotification\(["\']([^"\']+)["\']', 
                                         content[match.end():match.end()+200])
                
                message = message_match.group(1) if message_match else None
                
                validations.append(ValidationRule(
                    type='required' if '!' in validation_code else 'custom',
                    message=message,
                    condition=validation_code
                ))
        
        return validations
    
    def _find_label_for_input(self, content: str, input_pos: int) -> Optional[str]:
        """Find label text before input position"""
        # Look backwards for label
        search_start = max(0, input_pos - 500)
        search_content = content[search_start:input_pos]
        
        # Pattern for label
        label_pattern = r'<label[^>]*>([^<]+)</label>'
        matches = list(re.finditer(label_pattern, search_content))
        
        if matches:
            # Get the closest label
            last_match = matches[-1]
            return last_match.group(1).strip()
        
        return None
    
    def _extract_options(self, options_content: str) -> List[Dict[str, str]]:
        """Extract option elements from select"""
        options = []
        pattern = r'<option(?:\s+value=["\']([^"\']*)["\'])?[^>]*>([^<]*)</option>'
        matches = re.finditer(pattern, options_content)
        
        for match in matches:
            value = match.group(1) if match.group(1) else match.group(2)
            text = match.group(2).strip()
            
            options.append({
                'value': value,
                'text': text
            })
        
        return options
    
    def _extract_table_headers(self, table_content: str) -> List[str]:
        """Extract table headers"""
        headers = []
        
        # Look for thead section
        thead_match = re.search(r'<thead>(.*?)</thead>', table_content, re.DOTALL)
        if thead_match:
            thead_content = thead_match.group(1)
            
            # Extract th elements
            th_pattern = r'<th[^>]*>([^<]*)</th>'
            matches = re.finditer(th_pattern, thead_content)
            
            for match in matches:
                header_text = match.group(1).strip()
                # Remove sorting indicators
                header_text = re.sub(r'[⇅↑↓]', '', header_text).strip()
                if header_text and header_text != 'checkbox':
                    headers.append(header_text)
        
        return headers
    
    def _infer_type(self, value: str) -> str:
        """Infer data type from initial value"""
        if not value or value == 'null' or value == 'undefined':
            return 'unknown'
        
        if value.startswith('[') and value.endswith(']'):
            return 'array'
        
        if value.startswith('{') and value.endswith('}'):
            return 'object'
        
        if value in ['true', 'false']:
            return 'boolean'
        
        if value.startswith("'") or value.startswith('"'):
            return 'string'
        
        try:
            float(value)
            return 'number'
        except:
            pass
        
        return 'unknown'
    
    def to_json(self, analysis: ReactComponentAnalysis, indent: int = 2) -> str:
        """Convert analysis to JSON string"""
        def convert_to_dict(obj):
            if hasattr(obj, '__dict__'):
                result = {}
                for key, value in obj.__dict__.items():
                    if isinstance(value, list):
                        result[key] = [convert_to_dict(item) for item in value]
                    elif isinstance(value, dict):
                        result[key] = {k: convert_to_dict(v) for k, v in value.items()}
                    elif hasattr(value, '__dict__'):
                        result[key] = convert_to_dict(value)
                    else:
                        result[key] = value
                return result
            return obj
        
        data = convert_to_dict(analysis)
        return json.dumps(data, indent=indent, ensure_ascii=False)
    
    def save_json(self, analysis: ReactComponentAnalysis, output_path: str):
        """Save analysis to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json(analysis))


class LLMEnhancedComponentAnalyzer:
    """Enhanced component analyzer using LLM with RAG capabilities for business context"""
    
    def __init__(self, use_rag: bool = True):
        # Load environment variables
        load_dotenv()
        
        print("\nInitializing Enhanced Component Analyzer")
        print("=" * 50)
        
        # Get API key from Key Vault (with fallback to environment)
        azure_api_key = get_azure_openai_api_key_from_keyvault()
        if not azure_api_key:
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            print(" API Key Source: Environment Variable (.env file)")
        
        # Get other configuration from environment variables (.env file)
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        print("\nAzure OpenAI Configuration:")
        print(f"Endpoint: {azure_endpoint or 'Not configured'}")
        print(f"Deployment: {azure_deployment or 'Not configured'}")
        print(f"API Version: {azure_api_version}")
        print(f"API Key: {'Available' if azure_api_key else 'Missing'}")
        print(f"RAG Enabled: {'Yes' if use_rag else 'No'}")
        
        # Configure Azure OpenAI
        self.client = openai.AzureOpenAI(
            api_key=azure_api_key,
            api_version=azure_api_version,
            azure_endpoint=azure_endpoint
        )
        self.deployment_name = azure_deployment
        
        # Initialize RAG system if requested
        self.use_rag = use_rag
        self.rag_analyzer = None
        
        if self.use_rag:
            try:
                fine_tuning_folder = os.path.join(os.path.dirname(__file__), "Fine-Tuning-data")
                self.rag_analyzer = create_rag_enhanced_analyzer(
                    self.client, 
                    self.deployment_name, 
                    fine_tuning_folder
                )
                print("RAG system initialized successfully")
            except Exception as e:
                print(f"RAG initialization failed: {str(e)}")
                print("   → Falling back to standard LLM analysis")
                self.use_rag = False
        
        # Initialize base parser
        self.base_parser = ReactComponentParser()
    
    def analyze_with_llm(self, file_path: str) -> ReactComponentAnalysis:
        """Analyze React component using LLM for enhanced understanding"""
        
        # First get base analysis
        base_analysis = self.base_parser.parse_file(file_path)
        
        # Read the component file
        with open(file_path, 'r', encoding='utf-8') as f:
            component_content = f.read()
        
        # Enhance analysis with LLM
        enhanced_analysis = self._enhance_with_llm(component_content, base_analysis)
        
        return enhanced_analysis
    
    def enhance_existing_analysis(self, file_path: str, base_analysis: ReactComponentAnalysis) -> ReactComponentAnalysis:
        """Enhance an existing base analysis using LLM"""
        
        # Read the component file
        with open(file_path, 'r', encoding='utf-8') as f:
            component_content = f.read()
        
        # Enhance analysis with LLM
        enhanced_analysis = self._enhance_with_llm(component_content, base_analysis)
        
        return enhanced_analysis
    
    def _enhance_with_llm(self, component_content: str, base_analysis: ReactComponentAnalysis) -> ReactComponentAnalysis:
        """Use LLM to enhance the analysis with better understanding - now supports RAG for business context"""
        
        try:
            # Check if RAG is available and use it for enhancement
            if self.use_rag and self.rag_analyzer:
                print("Calling RAG-Enhanced LLM for enhancements...")
                
                # Use RAG-enhanced analysis for the entire component
                analysis_context = f"UI Component Analysis for {len(base_analysis.screens)} screens"
                enhanced_analysis = self.rag_analyzer.enhance_analysis_with_rag(
                    component_content, 
                    base_analysis, 
                    analysis_context
                )
                
                return enhanced_analysis
            else:
                # Fall back to standard LLM enhancement
                print("📝 Calling Standard LLM for enhancements...")
                return self._standard_llm_enhancement(component_content, base_analysis)
                
        except Exception as e:
            print(f"LLM enhancement failed: {str(e)}")
            print("   → Falling back to base analysis...")
            return base_analysis
    
    def _standard_llm_enhancement(self, component_content: str, base_analysis: ReactComponentAnalysis) -> ReactComponentAnalysis:
        """Standard LLM enhancement (fallback method)"""
        
        # Create enhanced analysis by cloning base analysis first
        enhanced_analysis = self._deep_copy_analysis(base_analysis)
        
        # Process screens individually to avoid token limits with large components
        total_screens = len(enhanced_analysis.screens)
        
        if total_screens > 0:
            print(f"  → Processing {total_screens} screen(s) individually for token limit safety...")
            
            for i, screen in enumerate(enhanced_analysis.screens, 1):
                print(f"  → Enhancing screen {i}/{total_screens}: {screen.name}")
                
                try:
                    # Extract only the relevant part of component content for this screen
                    screen_content = self._extract_screen_specific_content(component_content, screen.name)
                    
                    # Enhance this specific screen
                    enhanced_analysis.screens[i-1] = self._enhance_single_screen(screen_content, screen)
                    
                except Exception as e:
                    print(f"     Failed to enhance screen '{screen.name}': {str(e)}")
                    # Keep original screen if enhancement fails
                    continue
        
        print("  → Standard LLM enhancements completed for all screens")
        return enhanced_analysis
    
    def _deep_copy_analysis(self, analysis: ReactComponentAnalysis) -> ReactComponentAnalysis:
        """Create a deep copy of the analysis object for enhancement"""
        import copy
        return copy.deepcopy(analysis)
    
    def _extract_screen_specific_content(self, component_content: str, screen_name: str) -> str:
        """Extract only the relevant content for a specific screen to reduce token usage"""
        
        # Try to find the screen component definition
        screen_patterns = [
            rf'const\s+{screen_name}\s*=.*?(?=const\s+\w+|export|$)',
            rf'function\s+{screen_name}\s*\(.*?(?=function\s+\w+|export|$)',
            rf'{screen_name}\s*:\s*\(\).*?(?=\w+\s*:|export|$)'
        ]
        
        for pattern in screen_patterns:
            match = re.search(pattern, component_content, re.DOTALL | re.MULTILINE)
            if match:
                screen_content = match.group(0)
                # Limit to reasonable size (3000 chars) to avoid token limits
                if len(screen_content) > 3000:
                    screen_content = screen_content[:3000] + "..."
                return screen_content
        
        # Fallback: return a portion of the component around the screen name
        screen_position = component_content.find(screen_name)
        if screen_position != -1:
            start = max(0, screen_position - 500)
            end = min(len(component_content), screen_position + 2500)
            return component_content[start:end]
        
        # Last resort: return first part of component (truncated)
        return component_content[:2000] + "..."
    
    def _enhance_single_screen(self, screen_content: str, screen: Screen) -> Screen:
        """Enhance a single screen using LLM with token-limited content"""
        
        try:
            # Collect screen elements for analysis
            elements_info = []
            for elem in screen.elements:
                elem_info = {
                    'type': elem.element_type,
                    'label': elem.label,
                    'text': elem.text_content,
                    'attributes': {k: v for k, v in elem.attributes.items() if k in ['id', 'placeholder', 'className']}
                }
                elements_info.append(elem_info)
            
            prompt = f"""
Analyze this React screen component and enhance the analysis:

SCREEN: {screen.name}
CURRENT DESCRIPTION: {screen.description or 'None'}

SCREEN CODE:
{screen_content}

ELEMENTS FOUND: {len(elements_info)}
{json.dumps(elements_info[:10], indent=1)}

Provide ONLY a JSON object with enhancements:
{{
  "enhanced_description": "Better business-focused description of what this screen does",
  "element_enhancements": {{
    "element_id_or_text": {{
      "enhanced_label": "Better label",
      "business_purpose": "What this element does in business context",
      "ui_category": "primary|secondary|utility|navigation"
    }}
  }},
  "screen_purpose": "Main business purpose of this screen"
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert UI/UX analyst. Provide concise, business-focused enhancements for React components."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800  # Reasonable limit for single screen
            )
            
            result = self._parse_simple_json_response(response.choices[0].message.content)
            if result:
                # Apply enhancements to the screen
                if 'enhanced_description' in result and result['enhanced_description']:
                    screen.description = result['enhanced_description']
                
                # Add screen purpose as metadata
                if 'screen_purpose' in result:
                    if not hasattr(screen, 'business_purpose'):
                        screen.business_purpose = result['screen_purpose']
                
                # Apply element enhancements
                if 'element_enhancements' in result:
                    for elem in screen.elements:
                        # Try to match by ID, text content, or other attributes
                        elem_key = elem.attributes.get('id', elem.text_content or elem.label or '')
                        
                        if elem_key in result['element_enhancements']:
                            enhancement = result['element_enhancements'][elem_key]
                            
                            if 'enhanced_label' in enhancement and not elem.label:
                                elem.label = enhancement['enhanced_label']
                            
                            if 'business_purpose' in enhancement:
                                elem.attributes['business_purpose'] = enhancement['business_purpose']
                            
                            if 'ui_category' in enhancement:
                                elem.attributes['ui_category'] = enhancement['ui_category']
                
                print(f"    ✓ Enhanced screen: {screen.name}")
            
        except Exception as e:
            print(f"     Single screen enhancement failed for {screen.name}: {str(e)}")
        
        return screen
    

    
    def _enhance_element_labels(self, component_content: str, analysis: ReactComponentAnalysis) -> ReactComponentAnalysis:
        """Enhance element labels using LLM"""
        
        try:
            # Find elements without labels
            unlabeled_elements = []
            for screen in analysis.screens:
                for elem in screen.elements:
                    if elem.element_type in ['input', 'select'] and not elem.label:
                        elem_id = elem.attributes.get('id', elem.attributes.get('name', ''))
                        if elem_id:
                            unlabeled_elements.append({
                                'screen': screen.name,
                                'type': elem.element_type,
                                'id': elem_id,
                                'placeholder': elem.placeholder
                            })
            
            if unlabeled_elements:
                prompt = f"""
Based on this component code, suggest meaningful labels for these form elements:

ELEMENTS NEEDING LABELS:
{json.dumps(unlabeled_elements[:10], indent=2)}

CODE CONTEXT:
{component_content[:1500]}...

Provide ONLY a JSON object:
{{
  "suggested_labels": {{
    "element_id_1": "Meaningful Label Text",
    "element_id_2": "Meaningful Label Text"
  }}
}}
"""
                
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": "You are an expert form designer. Suggest clear, user-friendly labels for form elements."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=300
                )
                
                result = self._parse_simple_json_response(response.choices[0].message.content)
                if result and 'suggested_labels' in result:
                    for screen in analysis.screens:
                        for elem in screen.elements:
                            elem_id = elem.attributes.get('id', elem.attributes.get('name', ''))
                            if elem_id in result['suggested_labels']:
                                elem.label = result['suggested_labels'][elem_id]
                                
        except Exception as e:
            print(f"     Element label enhancement failed: {str(e)}")
        
        return analysis
    
    def _enhance_grid_sections(self, component_content: str, analysis: ReactComponentAnalysis) -> ReactComponentAnalysis:
        """Enhance grid section titles and descriptions using LLM"""
        
        try:
            # Find grids with items
            grid_items = []
            for screen in analysis.screens:
                for elem in screen.elements:
                    if elem.element_type == 'grid' and 'grid_items' in elem.attributes:
                        for item in elem.attributes['grid_items']:
                            if 'full_content' in item:
                                grid_items.append({
                                    'screen': screen.name,
                                    'content': item.get('full_content', '')[:200],
                                    'current_title': item.get('section_title', 'No Title')
                                })
            
            if grid_items:
                prompt = f"""
Analyze these dashboard/grid sections and suggest better titles and purposes:

GRID SECTIONS:
{json.dumps(grid_items[:8], indent=2)}

Provide ONLY a JSON object:
{{
  "enhanced_sections": [
    {{"original_title": "existing title", "enhanced_title": "Better Title", "purpose": "Brief purpose description"}},
  ]
}}
"""
                
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": "You are an expert dashboard designer. Improve section titles and identify their business purposes."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=400
                )
                
                result = self._parse_simple_json_response(response.choices[0].message.content)
                if result and 'enhanced_sections' in result:
                    # Apply enhancements to grid items
                    for screen in analysis.screens:
                        for elem in screen.elements:
                            if elem.element_type == 'grid' and 'grid_items' in elem.attributes:
                                for item in elem.attributes['grid_items']:
                                    for enhancement in result['enhanced_sections']:
                                        if item.get('section_title') == enhancement.get('original_title'):
                                            if 'enhanced_title' in enhancement:
                                                item['section_title'] = enhancement['enhanced_title']
                                            if 'purpose' in enhancement:
                                                item['business_purpose'] = enhancement['purpose']
                                
        except Exception as e:
            print(f"     Grid section enhancement failed: {str(e)}")
        
        return analysis
    
    def _enhance_button_purposes(self, component_content: str, analysis: ReactComponentAnalysis) -> ReactComponentAnalysis:
        """Enhance button purposes and descriptions using LLM"""
        
        try:
            # Find buttons
            buttons = []
            for screen in analysis.screens:
                for elem in screen.elements:
                    if elem.element_type == 'button':
                        buttons.append({
                            'screen': screen.name,
                            'text': elem.text_content,
                            'handler': next((action.handler for action in elem.actions if action.event == 'click'), '')
                        })
            
            if buttons:
                prompt = f"""
Analyze these buttons and suggest their business purposes:

BUTTONS:
{json.dumps(buttons[:15], indent=2)}

Provide ONLY a JSON object:
{{
  "button_purposes": [
    {{"text": "Button Text", "purpose": "Business purpose description", "category": "primary|secondary|danger|utility"}},
  ]
}}
"""
                
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": "You are an expert UX designer. Identify button purposes and categorize them."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=400
                )
                
                result = self._parse_simple_json_response(response.choices[0].message.content)
                if result and 'button_purposes' in result:
                    # Apply enhancements to buttons
                    for screen in analysis.screens:
                        for elem in screen.elements:
                            if elem.element_type == 'button':
                                for button_info in result['button_purposes']:
                                    if elem.text_content == button_info.get('text'):
                                        elem.attributes['business_purpose'] = button_info.get('purpose', '')
                                        elem.attributes['ui_category'] = button_info.get('category', '')
                                
        except Exception as e:
            print(f"     Button purpose enhancement failed: {str(e)}")
        
        return analysis
    
    def _parse_simple_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response with better error handling"""
        
        try:
            # Try direct parsing first
            return json.loads(response)
        except:
            pass
        
        # Extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # Find first JSON object
        json_start = response.find('{')
        if json_start != -1:
            brace_count = 0
            for i in range(json_start, len(response)):
                if response[i] == '{':
                    brace_count += 1
                elif response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            return json.loads(response[json_start:i+1])
                        except:
                            pass
                        break
        
        return None



def main():
    """Main function to run the UI Component Analyzer."""
    
    # Set up CLI argument parsing
    parser = argparse.ArgumentParser(
        description="Analyze React/TypeScript components and extract UI structure to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python step_1b_ui_component_analyzer_rag.py -i Inputs/ui_react_component.tsx -o JSON/ui_component_analysis.json
  python step_1b_ui_component_analyzer_rag.py -i Inputs/my_component.tsx -o JSON/my_analysis.json
        
Note: Both -i (input) and -o (output) arguments are required when calling from pipeline.
Default output: ui_component_analysis_base.json (generates both base + llm enhanced versions)
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        help='Path to the React/TypeScript component file or HTML file'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Path for the output JSON analysis file (default: JSON/ui_component_analysis_base.json)'
    )
    
    parser.add_argument(
        '--no-rag',
        action='store_true',
        help='Disable RAG enhancement and use standard LLM analysis only'
    )
    
    parser.add_argument(
        '--rag-only',
        action='store_true', 
        help='Use only RAG-enhanced analysis (skip standard LLM fallback)'
    )
    

    
    args = parser.parse_args()
    
    # Configuration - use CLI args or defaults
    current_dir = Path(__file__).parent
    inputs_dir = current_dir / "Inputs"
    json_output_dir = current_dir / "JSON"
    
    # Create directories if they don't exist
    inputs_dir.mkdir(exist_ok=True)
    json_output_dir.mkdir(exist_ok=True)
    
    if not args.input:
        print("Error: --input/-i argument is required. No hardcoded input file names allowed.")
        print("Please specify the input file using -i <input_file> or --input <input_file>")
        print("Example: python step_1b_ui_component_analyzer_rag.py -i Inputs/ui_react_component.tsx")
        return 1
        
    input_file = Path(args.input)
    if not input_file.is_absolute():
        input_file = current_dir / input_file
    
    if args.output:
        output_file = Path(args.output)
        if not output_file.is_absolute():
            output_file = current_dir / output_file
    else:
        output_file = json_output_dir / "ui_component_analysis_base.json"
    
    try:
        # Initialize analyzers
        print("Initializing UI Component Analyzer...")
        print(f"Input File: {input_file}")
        
        # Check if input file exists
        if not input_file.exists():
            print(f"Error: Component file not found: {input_file}")
            print("\nTo use this analyzer:")
            print(f"1. Place your React/TSX or HTML file in: {inputs_dir}")
            print("2. Name it 'ui_react_component.tsx' (or .html) or use -i to specify a different name")
            print("3. Run the script")
            return 1
        
        # Determine file type
        file_extension = input_file.suffix.lower()
        file_type = "HTML" if file_extension in ['.html', '.htm'] else "React/TSX"
        print(f"Detected file type: {file_type}")
        
        # Setup output files
        print(f"Base Output File: {output_file}")
        output_path = Path(output_file)
        
        # Generate LLM enhanced filename: replace '_base' with '_llm' or append '_llm' if no '_base'
        if '_base' in output_path.stem:
            llm_stem = output_path.stem.replace('_base', '_llm')
        else:
            llm_stem = f"{output_path.stem}_llm"
        llm_output_file = output_path.parent / f"{llm_stem}{output_path.suffix}"
        print(f"LLM Enhanced Output File: {llm_output_file}")
        
        # Step 1: Run base analysis first
        print(f"\nStep 1: Analyzing {file_type} component (base analysis)...")
        component_parser = ReactComponentParser()
        base_analysis = component_parser.parse_file(str(input_file))
        print(f"Base analysis completed")
        
        # Step 2: Run LLM-enhanced analysis using base results
        print(f"\nStep 2: Enhancing analysis with {'RAG-Enhanced ' if not args.no_rag else 'Standard '}LLM...")
        llm_analysis = None
        try:
            # Initialize analyzer with RAG configuration based on args
            use_rag = not args.no_rag
            llm_analyzer = LLMEnhancedComponentAnalyzer(use_rag=use_rag)
            
            llm_analysis = llm_analyzer.enhance_existing_analysis(str(input_file), base_analysis)
            
            # Print enhancement type used
            if llm_analyzer.use_rag and llm_analyzer.rag_analyzer:
                print(f"RAG-Enhanced LLM analysis completed")
            else:
                print(f"Standard LLM analysis completed")
                
        except Exception as e:
            print(f"LLM enhancement failed: {str(e)}")
            if not args.rag_only:
                print("   → LLM enhanced file will contain base analysis as fallback...")
                llm_analysis = base_analysis
            else:
                print("   → RAG-only mode: No fallback available")
                return 1
        
        # Print summary using base analysis
        if base_analysis:
            print(f"\n Analysis Summary:")
            print(f"  Component: {base_analysis.component_name}")
            print(f"  Screens found: {len(base_analysis.screens)}")
            print(f"  Global state variables: {len(base_analysis.global_state)}")
            print(f"  Global functions: {len(base_analysis.global_functions)}")
            
            for screen in base_analysis.screens:
                print(f"\n  Screen: {screen.name}")
                if screen.description:
                    print(f"     Description: {screen.description}")
                print(f"    Elements: {len(screen.elements)}")
                
                # Count by type
                element_counts = {}
                for elem in screen.elements:
                    element_counts[elem.element_type] = element_counts.get(elem.element_type, 0) + 1
                
                for elem_type, count in element_counts.items():
                    print(f"       - {elem_type}: {count}")
                
                # Show grid details if available
                grid_elements = [elem for elem in screen.elements if elem.element_type == 'grid']
                for grid in grid_elements:
                    grid_items = grid.attributes.get('grid_items', [])
                    if grid_items:
                        print(f"       Grid sections found:")
                        for item in grid_items:
                            if item.get('section_title'):
                                print(f"         - {item['section_title']}")
        
        # Step 3: Save both analyses
        print(f"\n Step 3: Saving analyses to JSON files...")
        
        # Save base analysis FIRST
        component_parser.save_json(base_analysis, str(output_file))
        print(f" Base analysis saved: {output_file.name}")
        
        # Save LLM-enhanced analysis SECOND
        if llm_analysis:
            # Use component_parser if llm_analyzer is not available (fallback scenario)
            parser_to_use = llm_analyzer if 'llm_analyzer' in locals() else component_parser
            if hasattr(parser_to_use, 'base_parser'):
                parser_to_use.base_parser.save_json(llm_analysis, str(llm_output_file))
            else:
                parser_to_use.save_json(llm_analysis, str(llm_output_file))
            print(f"  LLM-enhanced analysis saved: {llm_output_file.name}")
            
            # Compare file sizes to show they are different
            base_size = output_file.stat().st_size if output_file.exists() else 0
            enhanced_size = llm_output_file.stat().st_size if llm_output_file.exists() else 0
            
            print(f"\n File Comparison:")
            print(f"   Base analysis: {base_size:,} bytes")
            print(f"   LLM-enhanced: {enhanced_size:,} bytes")
            if enhanced_size != base_size:
                print(f"   Successfully created different enhanced version!")
            else:
                print(f"   Files are identical (enhancement may have failed)")
        
        print(f"\n UI Component analysis completed successfully!")
        print(f" Generated 2 files: Base analysis + LLM-enhanced analysis")
        
    except Exception as e:
        print(f" Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
