"""
Step 08: Frontend Code Generator
Generates React services, hooks, and wires the TSX component.
NO HARDCODING - reads all configuration from wired_ui.json.

Usage:
    python step_08_frontend_generator_gemini_llm_rewrite_v5.py <wired_ui.json> <input_tsx> <input_dir> <output_dir>

Example:
    python step_08_frontend_generator_gemini_llm_rewrite_v5.py wired_ui.json ui_react_component.tsx . ./output
"""

import json
import re
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional, Tuple


class FrontendCodeGenerator:
    """
    Generates frontend code based on wiring plan.
    All configuration comes from wired_ui.json - no hardcoding.
    """
    
    def __init__(
        self,
        wiring_plan: Dict[str, Any],
        input_dir: Path,
        output_dir: Path,
        tsx_metadata_path: Optional[Path] = None
    ):
        self.wiring = wiring_plan
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.tsx_metadata_path = tsx_metadata_path
        self.tsx_metadata = None
        
        # Load tsx_metadata if provided
        if tsx_metadata_path and tsx_metadata_path.exists():
            try:
                with open(tsx_metadata_path, 'r', encoding='utf-8') as f:
                    self.tsx_metadata = json.load(f)
                print(f"[INFO] Loaded TSX metadata: {tsx_metadata_path}")
            except Exception as e:
                print(f"[WARNING] Failed to load TSX metadata: {e}")
                self.tsx_metadata = None
        
        # Extract key info from wiring plan
        self.app_name = self.wiring.get('metadata', {}).get('app_name', 'App')
        self.entity_services = self.wiring.get('entity_services', [])
        self.screen_mappings = self.wiring.get('screen_mappings', [])
        self.mock_data_removal = self.wiring.get('mock_data_removal', [])
        
        # Derive names from config (no hardcoding)
        self.app_name_normalized = self._normalize_name(self.app_name)
        self.output_tsx_name = f"{self.app_name_normalized}_WIRED.tsx"
        
        # Setup directories
        self.src_dir = self.output_dir / "src"
        self.services_dir = self.src_dir / "services"
        self.hooks_dir = self.src_dir / "hooks"
        self.types_dir = self.src_dir / "types"
        
        for d in [self.output_dir, self.output_dir / "public", 
                  self.src_dir, self.services_dir, self.hooks_dir, self.types_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def generate(self):
        """Main generation method."""
        print(f"\n{'='*60}")
        print(f"--- Step 08: Frontend Code Generation (No Hardcoding) ---")
        print(f"{'='*60}")
        print(f"App Name: {self.app_name}")
        print(f"Output TSX: {self.output_tsx_name}")
        
        # 1. Generate type definitions
        self._generate_types()
        
        # 2. Generate services
        self._generate_services()
        
        # 3. Generate hooks with validations
        self._generate_hooks()
        
        # 4. Generate infrastructure
        self._generate_infrastructure()
        
        # 5. Process and wire TSX
        self._process_tsx()
        
        print(f"\n[SUCCESS] Generation complete!")
        print(f"Output directory: {self.output_dir}")
    
    def _normalize_name(self, name: str) -> str:
        """Convert name to PascalCase."""
        return ''.join(
            word.capitalize() 
            for word in re.split(r'[^a-zA-Z0-9]+', name) 
            if word
        )
    
    def _generate_screen_form_type_name(self, story_id: str) -> str:
        """Generate type name for screen-specific FormData."""
        return f"{self._normalize_name(story_id.replace(' ', ''))}FormData"
    
    def _generate_screen_form_type(self, story_id: str, field_mappings: List[Dict]) -> str:
        """Generate TypeScript interface for screen-specific form data."""
        type_name = self._generate_screen_form_type_name(story_id)
        fields = []
        
        for mapping in field_mappings:
            binding = mapping.get('config_binding', '')
            field_id = self._extract_column_from_binding(binding)
            if not field_id:
                field_id = mapping.get('config_field_id', '')
            
            if field_id:
                # Infer type from validations
                field_type = self._infer_field_type(mapping)
                fields.append(f"  {field_id}?: {field_type};")
        
        if not fields:
            return f"interface {type_name} {{\n  [key: string]: any;\n}}"
        
        return f"interface {type_name} {{\n" + "\n".join(fields) + "\n}"
    
    def _infer_field_type(self, mapping: Dict) -> str:
        """Infer TypeScript type from field mapping."""
        validations = mapping.get('validations', [])
        for validation in validations:
            rule = validation.get('rule', '').lower()
            if 'number' in rule or 'integer' in rule or 'positive' in rule:
                return 'number'
            if 'boolean' in rule:
                return 'boolean'
        return 'string'
    
    def _to_camel_case(self, name: str) -> str:
        """Convert name to camelCase."""
        pascal = self._normalize_name(name)
        if pascal:
            return pascal[0].lower() + pascal[1:]
        return ''
    
    def _extract_column_from_binding(self, binding: str) -> str:
        """
        Extract column name from binding string for data operations.
        
        This ensures formData properties match actual database columns,
        supporting multi-language UI labels while maintaining correct data layer.
        
        Args:
            binding: Binding string in format 'table.column' or 'column'
            
        Returns:
            Column name to use for formData properties
            
        Examples:
            >>> self._extract_column_from_binding('nsi_items.disposition')
            'disposition'
            >>> self._extract_column_from_binding('inventory.item_id')
            'item_id'
            >>> self._extract_column_from_binding('status')
            'status'
        """
        if not binding:
            return ''
        
        # Handle 'table.column' format
        if '.' in binding:
            parts = binding.rsplit('.', 1)
            return parts[1] if len(parts) == 2 else binding
        
        # Handle plain 'column' format
        return binding
    
    def _generate_types(self):
        """Generate TypeScript type definitions from entity schemas."""
        print("\n[1] Generating type definitions...")
        
        types_content = [
            "// Auto-generated type definitions",
            "// DO NOT EDIT - Generated by step_08_frontend_generator",
            ""
        ]
        
        for service in self.entity_services:
            entity_name = service['entity_name']
            class_name = self._normalize_name(entity_name)
            fields = service.get('fields', [])
            pk = service.get('primary_key', 'id')
            pk_type = self._map_to_ts_type(service.get('primary_key_type', 'int'))
            
            # Generate interface
            types_content.append(f"export interface {class_name} {{")
            
            for field in fields:
                field_name = field['name']
                ts_type = field.get('typescript_type', 'any')
                nullable = field.get('nullable', True)
                
                optional = '?' if nullable or field_name == pk else ''
                types_content.append(f"  {field_name}{optional}: {ts_type};")
            
            types_content.append("}")
            types_content.append("")
            
            # Generate Create DTO (exclude auto-generated fields)
            types_content.append(f"export interface {class_name}Create {{")
            for field in fields:
                if field.get('auto_increment') or field.get('primary_key'):
                    continue
                if field.get('default') and field['name'] in ['created_date', 'modified_date']:
                    continue
                
                field_name = field['name']
                ts_type = field.get('typescript_type', 'any')
                nullable = field.get('nullable', True)
                has_default = field.get('default') is not None
                
                optional = '?' if nullable or has_default else ''
                types_content.append(f"  {field_name}{optional}: {ts_type};")
            
            types_content.append("}")
            types_content.append("")
        
        # Write types file
        types_file = self.types_dir / "entities.ts"
        types_file.write_text('\n'.join(types_content), encoding='utf-8')
        print(f"  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated {types_file.name}")
    
    def _map_to_ts_type(self, type_str: str) -> str:
        """Map type string to TypeScript type."""
        type_map = {
            'int': 'number',
            'str': 'string',
            'float': 'number',
            'bool': 'boolean',
            'datetime': 'string',
            'date': 'string',
            'UUID': 'string',
            'Decimal': 'number',
        }
        return type_map.get(type_str, 'any')
    
    def _generate_services(self):
        """Generate API service files for each entity."""
        print("\n[2] Generating services...")
        
        # Generate API client
        api_client_content = """// Auto-generated API client
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth tokens
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;
"""
        (self.services_dir / 'apiClient.ts').write_text(api_client_content, encoding='utf-8')
        print(f"  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated apiClient.ts")
        
        # Generate service for each entity
        for service in self.entity_services:
            self._generate_entity_service(service)
    
    def _generate_entity_service(self, service: Dict[str, Any]):
        """Generate service file for a single entity."""
        entity_name = service['entity_name']
        service_name = service['service_name']
        class_name = self._normalize_name(entity_name)
        pk = service.get('primary_key', 'id')
        pk_type = self._map_to_ts_type(service.get('primary_key_type', 'int'))
        
        # Find APIs for this entity
        apis = service.get('apis', [])
        
        # Determine base endpoint from APIs or entity name
        base_endpoint = f"/api/v1/{entity_name}"
        for api in apis:
            endpoint = api.get('endpoint', '')
            if '/{' not in endpoint and endpoint:
                base_endpoint = endpoint.rstrip('/')
                break
        
        service_content = f"""// Auto-generated service for {entity_name}
import apiClient from './apiClient';
import {{ {class_name}, {class_name}Create }} from '../types/entities';

export interface ApiResponse<T> {{
  data: T;
  message?: string;
}}

export interface PaginatedResponse<T> {{
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}}

const {service_name} = {{
  /**
   * Get all {entity_name} records
   */
  getAll: async (): Promise<{class_name}[]> => {{
    const response = await apiClient.get('{base_endpoint}/');
    return response.data;
  }},

  /**
   * Get a single {entity_name} by {pk}
   */
  getById: async ({pk}: {pk_type}): Promise<{class_name}> => {{
    const response = await apiClient.get(`{base_endpoint}/${{{pk}}}`);
    return response.data;
  }},

  /**
   * Create a new {entity_name}
   */
  create: async (data: {class_name}Create): Promise<{class_name}> => {{
    const response = await apiClient.post('{base_endpoint}/', data);
    return response.data;
  }},

  /**
   * Update an existing {entity_name}
   */
  update: async ({pk}: {pk_type}, data: Partial<{class_name}>): Promise<{class_name}> => {{
    const response = await apiClient.put(`{base_endpoint}/${{{pk}}}`, data);
    return response.data;
  }},

  /**
   * Delete a {entity_name}
   */
  delete: async ({pk}: {pk_type}): Promise<boolean> => {{
    await apiClient.delete(`{base_endpoint}/${{{pk}}}`);
    return true;
  }},
}};

export default {service_name};
"""
        
        service_file = self.services_dir / f"{service_name}.ts"
        service_file.write_text(service_content, encoding='utf-8')
        print(f"  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated {service_name}.ts")
    
    def _generate_hooks(self):
        """Generate React hooks for each screen with validations."""
        print("\n[3] Generating hooks...")
        
        for screen_mapping in self.screen_mappings:
            self._generate_screen_hook(screen_mapping)
    
    def _generate_screen_hook(self, screen_mapping: Dict[str, Any]):
        """Generate hook for a single screen."""
        story_id = screen_mapping['story_id']
        tsx_screen_name = screen_mapping['tsx_screen_name']
        primary_entity = screen_mapping.get('primary_entity', '')
        field_mappings = screen_mapping.get('field_mappings', [])
        handler_mappings = screen_mapping.get('handler_mappings', [])
        
        # Normalize names
        hook_name = f"use{self._normalize_name(story_id.replace(' ', ''))}Logic"
        entity_class = self._normalize_name(primary_entity)
        service_name = f"{entity_class}Service"
        
        # Build validation logic from field mappings
        validation_code = self._build_validation_code(field_mappings)
        
        # Build field extraction code
        field_extraction = self._build_field_extraction_code(field_mappings)
        
        # Generate custom FormData type for this screen
        form_type_def = self._generate_screen_form_type(story_id, field_mappings)
        
        # Build default values from entity schema
        defaults_code = self._build_defaults_code(primary_entity)
        
        # Determine which handlers to generate
        form_type_name = self._generate_screen_form_type_name(story_id)
        handler_code = self._build_handler_code(handler_mappings, service_name, entity_class, form_type_name)
        
        hook_content = f"""// Auto-generated hook for {story_id}
// Screen: {tsx_screen_name}
import {{ useState, useCallback }} from 'react';
import {service_name} from '../services/{service_name}';
import {{ {entity_class}, {entity_class}Create }} from '../types/entities';

interface ValidationError {{
  field: string;
  message: string;
}}

// Screen-specific FormData type (supports fields from multiple tables)
{form_type_def}

interface UseLogicResult {{
  loading: boolean;
  errors: ValidationError[];
  {self._build_handler_type_signatures(handler_mappings)}
}}

export const {hook_name} = (
  showNotification: (message: string, type: 'success' | 'danger' | 'warning') => void
): UseLogicResult => {{
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<ValidationError[]>([]);

  /**
   * Validate form data against business rules
   */
  const validateForm = useCallback((formData: {self._generate_screen_form_type_name(story_id)}): ValidationError[] => {{
    const validationErrors: ValidationError[] = [];
    
{validation_code}
    
    return validationErrors;
  }}, []);

  {handler_code}

  return {{
    loading,
    errors,
    {self._build_handler_return_list(handler_mappings)}
  }};
}};

export default {hook_name};
"""
        
        hook_file = self.hooks_dir / f"{hook_name}.ts"
        hook_file.write_text(hook_content, encoding='utf-8')
        print(f"  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated {hook_name}.ts")
    
    def _build_validation_code(self, field_mappings: List[Dict]) -> str:
        """Build validation code from field mappings."""
        lines = []
        
        for mapping in field_mappings:
            # Extract column name from binding for consistency with formData
            binding = mapping.get('config_binding', '')
            field_id = self._extract_column_from_binding(binding)
            
            # Fallback to config_field_id if binding extraction fails
            if not field_id:
                field_id = mapping.get('config_field_id', '')
            
            validations = mapping.get('validations', [])
            error_messages = mapping.get('error_messages', {})
            tsx_id = mapping.get('tsx_id', '')
            
            for validation in validations:
                rule = validation.get('rule', '')
                is_required = validation.get('required', False)
                error_msg = validation.get('error_message', f'{field_id} is invalid')
                
                if is_required or 'required' in rule.lower() or 'must be present' in rule.lower():
                    lines.append(f"""    // Validation: {rule}
    if (!formData.{field_id} || formData.{field_id}.toString().trim() === '') {{
      validationErrors.push({{
        field: '{tsx_id}',
        message: '{error_msg}'
      }});
    }}
""")
                
                if 'positive' in rule.lower() and 'integer' in rule.lower():
                    lines.append(f"""    // Validation: {rule}
    if (formData.{field_id} !== undefined && (isNaN(Number(formData.{field_id})) || Number(formData.{field_id}) < 1)) {{
      validationErrors.push({{
        field: '{tsx_id}',
        message: '{error_msg}'
      }});
    }}
""")
        
        return '\n'.join(lines) if lines else '    // No validations defined'
    
    def _build_field_extraction_code(self, field_mappings: List[Dict]) -> str:
        """Build code to extract field values from DOM."""
        lines = []
        
        for mapping in field_mappings:
            tsx_id = mapping.get('tsx_id', '')
            # Extract column name from binding
            binding = mapping.get('config_binding', '')
            config_id = self._extract_column_from_binding(binding)
            
            # Fallback to config_field_id if binding extraction fails
            if not config_id:
                config_id = mapping.get('config_field_id', '')
            
            if tsx_id and config_id:
                lines.append(
                    f"    {config_id}: (document.getElementById('{tsx_id}') as HTMLInputElement | null)?.value || '',"
                )
        
        return '\n'.join(lines)
    
    def _build_defaults_code(self, entity_name: str) -> str:
        """Build default values code from entity schema."""
        defaults = []
        
        # Find entity in services
        for service in self.entity_services:
            if service['entity_name'] == entity_name:
                for field in service.get('fields', []):
                    default_val = field.get('default')
                    if default_val and not field.get('auto_increment'):
                        field_name = field['name']
                        
                        # Handle special defaults
                        if default_val == 'CURRENT_TIMESTAMP':
                            defaults.append(f"      {field_name}: new Date().toISOString(),")
                        elif default_val == 'gen_random_uuid()':
                            continue  # Let server generate
                        elif default_val.isdigit():
                            defaults.append(f"      {field_name}: {default_val},")
                        else:
                            defaults.append(f"      {field_name}: '{default_val}',")
                break
        
        return '\n'.join(defaults) if defaults else ''
    
    def _build_handler_code(
        self, 
        handler_mappings: List[Dict],
        service_name: str,
        entity_class: str,
        form_type_name: str
    ) -> str:
        """Build handler function code."""
        handlers = []
        
        for mapping in handler_mappings:
            tsx_func = mapping.get('tsx_function_name', '')
            api_method = mapping.get('target_api_method', 'POST')
            api_endpoint = mapping.get('target_api_endpoint', '')
            
            if api_method == 'POST':
                handlers.append(self._build_create_handler(
                    tsx_func, service_name, entity_class, form_type_name
                ))
            elif api_method == 'PUT':
                handlers.append(self._build_update_handler(
                    tsx_func, service_name, entity_class
                ))
            elif api_method == 'DELETE':
                handlers.append(self._build_delete_handler(
                    tsx_func, service_name, entity_class
                ))
        
        # If no handlers mapped, create a generic one based on screen context
        if not handlers:
            handlers.append(self._build_generic_handler(service_name, entity_class, form_type_name))
        
        return '\n\n'.join(handlers)
    
    def _build_create_handler(
        self, 
        func_name: str, 
        service_name: str, 
        entity_class: str,
        form_type_name: str
    ) -> str:
        """Build create/POST handler."""
        return f"""  /**
   * Handle create operation
   */
  const {func_name} = useCallback(async (formData: {form_type_name}): Promise<{entity_class} | null> => {{
    // Validate
    const validationErrors = validateForm(formData);
    if (validationErrors.length > 0) {{
      setErrors(validationErrors);
      validationErrors.forEach(err => {{
        showNotification(err.message, 'danger');
      }});
      return null;
    }}

    setLoading(true);
    setErrors([]);

    try {{
      // Convert formData to API format (entity type)
      const apiData = formData as any;  // Type assertion for API call
      const result = await {service_name}.create(apiData);
      showNotification('Item created successfully', 'success');
      return result;
    }} catch (error: any) {{
      const message = error.response?.data?.detail 
        ? JSON.stringify(error.response.data.detail) 
        : error.message;
      showNotification(`Operation failed: ${{message}}`, 'danger');
      return null;
    }} finally {{
      setLoading(false);
    }}
  }}, [validateForm, showNotification]);"""
    
    def _build_update_handler(
        self, 
        func_name: str, 
        service_name: str, 
        entity_class: str
    ) -> str:
        """Build update/PUT handler."""
        return f"""  /**
   * Handle update operation
   */
  const {func_name} = useCallback(async (id: number | string, formData: Partial<{entity_class}>): Promise<{entity_class} | null> => {{
    setLoading(true);
    setErrors([]);

    try {{
      const result = await {service_name}.update(id as any, formData);
      showNotification('Item updated successfully', 'success');
      return result;
    }} catch (error: any) {{
      const message = error.response?.data?.detail 
        ? JSON.stringify(error.response.data.detail) 
        : error.message;
      showNotification(`Update failed: ${{message}}`, 'danger');
      return null;
    }} finally {{
      setLoading(false);
    }}
  }}, [showNotification]);"""
    
    def _build_delete_handler(
        self, 
        func_name: str, 
        service_name: str, 
        entity_class: str
    ) -> str:
        """Build delete handler."""
        return f"""  /**
   * Handle delete operation
   */
  const {func_name} = useCallback(async (id: number | string): Promise<boolean> => {{
    setLoading(true);

    try {{
      await {service_name}.delete(id as any);
      showNotification('Item deleted successfully', 'success');
      return true;
    }} catch (error: any) {{
      const message = error.response?.data?.detail 
        ? JSON.stringify(error.response.data.detail) 
        : error.message;
      showNotification(`Delete failed: ${{message}}`, 'danger');
      return false;
    }} finally {{
      setLoading(false);
    }}
  }}, [showNotification]);"""
    
    def _build_generic_handler(self, service_name: str, entity_class: str, form_type_name: str = None) -> str:
        """Build generic create handler when no specific mapping exists."""
        if not form_type_name:
            form_type_name = f"{entity_class}Create"
        
        return f"""  /**
   * Handle form submission
   */
  const processSubmit = useCallback(async (formData: {form_type_name}): Promise<{entity_class} | null> => {{
    // Validate
    const validationErrors = validateForm(formData);
    if (validationErrors.length > 0) {{
      setErrors(validationErrors);
      validationErrors.forEach(err => {{
        showNotification(err.message, 'danger');
      }});
      return null;
    }}

    setLoading(true);
    setErrors([]);

    try {{
      const apiData = formData as any;  // Type assertion for API call
      const result = await {service_name}.create(apiData);
      showNotification('Operation successful', 'success');
      return result;
    }} catch (error: any) {{
      const message = error.response?.data?.detail 
        ? JSON.stringify(error.response.data.detail) 
        : error.message;
      showNotification(`Operation failed: ${{message}}`, 'danger');
      return null;
    }} finally {{
      setLoading(false);
    }}
  }}, [validateForm, showNotification]);"""
    
    def _build_handler_type_signatures(self, handler_mappings: List[Dict]) -> str:
        """Build TypeScript type signatures for handlers."""
        signatures = []
        
        for mapping in handler_mappings:
            func_name = mapping.get('tsx_function_name', '')
            api_method = mapping.get('target_api_method', 'POST')
            
            if api_method == 'POST':
                signatures.append(f"{func_name}: (formData: any) => Promise<any>;")
            elif api_method == 'PUT':
                signatures.append(f"{func_name}: (id: any, formData: any) => Promise<any>;")
            elif api_method == 'DELETE':
                signatures.append(f"{func_name}: (id: any) => Promise<boolean>;")
        
        if not signatures:
            signatures.append("processSubmit: (formData: any) => Promise<any>;")
        
        return '\n  '.join(signatures)
    
    def _build_handler_return_list(self, handler_mappings: List[Dict]) -> str:
        """Build list of handlers to return from hook."""
        handlers = [m.get('tsx_function_name', '') for m in handler_mappings if m.get('tsx_function_name')]
        
        if not handlers:
            handlers = ['processSubmit']
        
        return ',\n    '.join(handlers)
    
    def _generate_infrastructure(self):
        """Generate package.json, tsconfig, etc."""
        print("\n[4] Generating infrastructure files...")
        
        # package.json
        pkg = {
            "name": self._to_camel_case(self.app_name),
            "version": "1.0.0",
            "private": True,
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-scripts": "5.0.1",
                "axios": "^1.6.0",
                "typescript": "^4.9.5"
            },
            "devDependencies": {
                "@types/react": "^18.2.0",
                "@types/react-dom": "^18.2.0"
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test"
            },
            "browserslist": [">0.2%", "not dead", "not op_mini all"]
        }
        (self.output_dir / 'package.json').write_text(
            json.dumps(pkg, indent=2), encoding='utf-8'
        )
        print("  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated package.json")
        
        # tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "target": "es5",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "strict": True,
                "forceConsistentCasingInFileNames": True,
                "noFallthroughCasesInSwitch": True,
                "module": "esnext",
                "moduleResolution": "node",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "noEmit": True,
                "jsx": "react-jsx"
            },
            "include": ["src"]
        }
        (self.output_dir / 'tsconfig.json').write_text(
            json.dumps(tsconfig, indent=2), encoding='utf-8'
        )
        print("  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated tsconfig.json")
        
        # .env
        (self.output_dir / '.env').write_text(
            "REACT_APP_API_URL=http://localhost:8000", encoding='utf-8'
        )
        print("  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated .env")
        
        # public/index.html
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{self.app_name}</title>
</head>
<body>
  <noscript>You need to enable JavaScript to run this app.</noscript>
  <div id="root"></div>
</body>
</html>
"""
        (self.output_dir / "public" / "index.html").write_text(html, encoding='utf-8')
        print("  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated public/index.html")
        
        # src/index.tsx
        index_tsx = f"""import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './{self.output_tsx_name[:-4]}';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
        (self.src_dir / "index.tsx").write_text(index_tsx, encoding='utf-8')
        print("  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated src/index.tsx")
        
        # react-app-env.d.ts
        (self.src_dir / 'react-app-env.d.ts').write_text(
            '/// <reference types="react-scripts" />', encoding='utf-8'
        )
        print("  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated react-app-env.d.ts")
    
    def _process_tsx(self):
        """Process and wire the TSX file."""
        print("\n[5] Processing TSX file...")
        
        # Find input TSX file
        input_tsx_candidates = [
            self.input_dir / "ui_react_component.tsx",
            self.input_dir / f"{self.app_name_normalized}.tsx",
        ]
        
        input_tsx = None
        for candidate in input_tsx_candidates:
            if candidate.exists():
                input_tsx = candidate
                break
        
        if not input_tsx:
            # Search for any .tsx file
            tsx_files = list(self.input_dir.glob("*.tsx"))
            if tsx_files:
                input_tsx = tsx_files[0]
        
        if not input_tsx or not input_tsx.exists():
            print(f"  [WARNING] No input TSX file found in {self.input_dir}")
            return
        
        print(f"  Input: {input_tsx}")
        
        # Read content
        content = input_tsx.read_text(encoding='utf-8')
        lines = content.splitlines()
        
        # Process in order (ID injection FIRST to preserve line numbers from metadata)
        lines = self._add_missing_input_ids(lines)
        lines = self._remove_mock_data(lines)
        lines = self._inject_imports(lines)
        lines = self._inject_hook_calls_at_component_level(lines)  # NEW: Inject hooks AFTER showNotification
        lines = self._wire_handlers(lines)
        lines = self._add_api_data_loading(lines)
        
        # Apply TypeScript fixes
        final_content = '\n'.join(lines)
        final_content = self._fix_typescript_types(final_content)
        
        # Write output
        output_path = self.src_dir / self.output_tsx_name
        output_path.write_text(final_content, encoding='utf-8')
        print(f"  ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Generated {self.output_tsx_name}")
    
    def _add_missing_input_ids(self, lines: List[str]) -> List[str]:
        """
        Inject IDs into TSX fields that were auto-generated by Step 06.
        
        This method finds all fields in tsx_metadata with 'id_generated: true'
        and injects the ID attribute into the corresponding TSX line.
        
        Args:
            lines: TSX file content as list of lines (0-indexed)
            
        Returns:
            Modified lines with IDs injected
            
        Example:
            Input:  <input type="checkbox" />
            Output: <input id="dashboardField256" type="checkbox" />
        """
        if not self.tsx_metadata:
            print("  - Skipping ID injection (no tsx_metadata provided)")
            return lines
        
        print("  - Injecting missing IDs from tsx_metadata.json...")
        
        # Extract all fields that need ID injection
        fields_to_inject = []
        screens = self.tsx_metadata.get('screens', [])
        
        for screen in screens:
            for field in screen.get('fields', []):
                if field.get('id_generated', False):
                    fields_to_inject.append(field)
        
        if not fields_to_inject:
            print("    [INFO] No fields require ID injection")
            return lines
        
        # Inject IDs
        injected_count = 0
        skipped_count = 0
        
        for field in fields_to_inject:
            tsx_id = field.get('tsx_id')
            line_number = field.get('line_number')  # 1-indexed
            element_type = field.get('element_type', 'input')
            
            if not tsx_id or not line_number:
                skipped_count += 1
                continue
            
            # Convert to 0-indexed
            line_index = line_number - 1
            
            # Validate line index
            if line_index < 0 or line_index >= len(lines):
                print(f"    [WARN] Line {line_number} out of bounds for field '{tsx_id}'")
                skipped_count += 1
                continue
            
            # Get the line
            original_line = lines[line_index]
            
            # Create regex pattern to inject ID as first attribute
            # Matches: <input ...> or <select ...> or <textarea ...>
            # Captures: opening tag, existing attributes, closing
            pattern = rf'(<{element_type}\s+)(.*?)(/?>\s*)$'
            
            # Check if line matches pattern
            match = re.search(pattern, original_line, re.IGNORECASE)
            if not match:
                # Try pattern without space after tag name (e.g., <input/>)
                pattern_no_space = rf'(<{element_type})(/?>\s*)$'
                match_no_space = re.search(pattern_no_space, original_line, re.IGNORECASE)
                
                if match_no_space:
                    # Inject ID when no existing attributes
                    replacement = rf'\1 id="{tsx_id}"\2'
                    modified_line = re.sub(pattern_no_space, replacement, original_line, flags=re.IGNORECASE)
                    lines[line_index] = modified_line
                    print(f"    ÃƒÂ¢Ã…â€œÃ¢â‚¬Å“ Injected ID '{tsx_id}' at line {line_number}")
                    injected_count += 1
                else:
                    print(f"    [WARN] Pattern mismatch at line {line_number} for field '{tsx_id}'")
                    skipped_count += 1
                continue
            
            # Inject ID as first attribute
            # Format: <input id="tsx_id" existing_attributes />
            replacement = rf'\1id="{tsx_id}" \2\3'
            modified_line = re.sub(pattern, replacement, original_line, flags=re.IGNORECASE)
            
            # Update the line
            lines[line_index] = modified_line
            print(f"    ÃƒÂ¢Ã…â€œÃ¢â‚¬Å“ Injected ID '{tsx_id}' at line {line_number}")
            injected_count += 1
        
        # Summary
        print(f"    [INFO] ID injection complete: {injected_count} injected, {skipped_count} skipped")
        
        return lines
    
    def _remove_mock_data(self, lines: List[str]) -> List[str]:
        """Remove mock data from useState declarations."""
        print("  - Removing mock data...")
        
        for mock_loc in self.mock_data_removal:
            var_name = mock_loc.get('variable_name', '')
            action = mock_loc.get('action', 'replace_with_empty_array')
            
            # Find the useState line for this variable
            for i, line in enumerate(lines):
                if f'const [{var_name},' in line and 'useState' in line:
                    # Find the end of this statement
                    start_line = i
                    bracket_count = 0
                    in_statement = False
                    end_line = i
                    
                    for j in range(i, min(i + 100, len(lines))):
                        for char in lines[j]:
                            if char == '[':
                                bracket_count += 1
                                in_statement = True
                            elif char == ']':
                                bracket_count -= 1
                        
                        if in_statement and bracket_count == 0:
                            end_line = j
                            break
                    
                    # Replace with empty array
                    setter_name = f"set{var_name[0].upper()}{var_name[1:]}"
                    replacement = f"  const [{var_name}, {setter_name}] = useState<any[]>([]);"
                    
                    lines = lines[:start_line] + [replacement] + lines[end_line + 1:]
                    print(f"    ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Cleared mock data from {var_name}")
                    break
        
        return lines
    
    def _inject_imports(self, lines: List[str]) -> List[str]:
        """Inject service and hook imports."""
        print("  - Injecting imports...")
        
        new_imports = [
            "",
            "// Auto-generated imports",
        ]
        
        # Add service imports
        for service in self.entity_services:
            service_name = service['service_name']
            new_imports.append(f"import {service_name} from './services/{service_name}';")
        
        # Add hook imports
        for screen in self.screen_mappings:
            story_id = screen['story_id']
            hook_name = f"use{self._normalize_name(story_id.replace(' ', ''))}Logic"
            new_imports.append(f"import {{ {hook_name} }} from './hooks/{hook_name}';")
        
        # Add type imports
        entity_names = [self._normalize_name(s['entity_name']) for s in self.entity_services]
        if entity_names:
            new_imports.append(f"import {{ {', '.join(entity_names)} }} from './types/entities';")
        
        new_imports.append("")
        
        # Find last import line
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('import '):
                last_import_idx = i
        
        if last_import_idx >= 0:
            return lines[:last_import_idx + 1] + new_imports + lines[last_import_idx + 1:]
        else:
            return new_imports + lines
    
    def _wire_handlers(self, lines: List[str]) -> List[str]:
        """Wire handler functions to use hooks."""
        print("  - Wiring handlers...")
        
        for screen in self.screen_mappings:
            for handler in screen.get('handler_mappings', []):
                tsx_func = handler.get('tsx_function_name', '')
                if tsx_func:
                    lines = self._wire_single_handler(lines, tsx_func, screen)
        
        return lines
    
    def _wire_single_handler(
        self, 
        lines: List[str], 
        handler_name: str,
        screen: Dict
    ) -> List[str]:
        """Wire a single handler function."""
        story_id = screen['story_id']
        hook_name = f"use{self._normalize_name(story_id.replace(' ', ''))}Logic"
        field_mappings = screen.get('field_mappings', [])
        
        # Find the handler function
        handler_start = -1
        for i, line in enumerate(lines):
            if f'const {handler_name} =' in line or f'const {handler_name}=' in line:
                handler_start = i
                break
        
        if handler_start == -1:
            print(f"    [INFO] Handler '{handler_name}' not found in TSX")
            return lines
        
        # Find the end of the handler
        handler_end = self._find_function_end(lines, handler_start)
        
        # Build field extraction code
        field_extractions = []
        form_data_fields = []
        
        for mapping in field_mappings:
            tsx_id = mapping.get('tsx_id', '')
            # Extract column name from binding for proper data layer mapping
            binding = mapping.get('config_binding', '')
            column_name = self._extract_column_from_binding(binding)
            
            # Fallback to config_field_id if binding extraction fails (backwards compatibility)
            if not column_name:
                column_name = mapping.get('config_field_id', '')
            
            if tsx_id and column_name:
                field_extractions.append(
                    f"    const {column_name}Value = (document.getElementById('{tsx_id}') as HTMLInputElement | null)?.value || '';"
                )
                form_data_fields.append(f"      {column_name}: {column_name}Value,")
        
        # Build new handler
        # Use 'handle' prefix to prevent shadowing the hook function
        # Hook function: addToWorklist
        # DOM handler: handleAddToWorklist
        handler_wrapper_name = f"handle{handler_name[0].upper()}{handler_name[1:]}"
        
        new_handler = [
            f"  const {handler_wrapper_name} = async () => {{",
            "",
        ]
        new_handler.extend(field_extractions)
        new_handler.append("")
        new_handler.append("    const formData = {")
        new_handler.extend(form_data_fields)
        new_handler.append("    };")
        new_handler.append("")
        new_handler.append(f"    const result = await {handler_name}(formData);")
        new_handler.append("")
        new_handler.append("    if (result) {")
        new_handler.append("      // Update local state if needed")
        new_handler.append(f"      // setWorklistItems(prev => [...prev, result]);")
        new_handler.append("    }")
        new_handler.append("  };")
        new_handler.append("")
        
        # Replace old handler with new
        lines = lines[:handler_start] + new_handler + lines[handler_end + 1:]
        print(f"    ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Wired {handler_name} ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ {hook_name}")
        
        # Update onClick references to use the new handler name with 'handle' prefix
        handler_wrapper_name = f"handle{handler_name[0].upper()}{handler_name[1:]}"
        for i in range(len(lines)):
            # Update direct onClick references
            if f'onClick={{{handler_name}}}' in lines[i]:
                lines[i] = lines[i].replace(f'onClick={{{handler_name}}}' , f'onClick={{{handler_wrapper_name}}}')
            # Update onClick with spaces
            if f'onClick={{ {handler_name} }}' in lines[i]:
                lines[i] = lines[i].replace(f'onClick={{ {handler_name} }}' , f'onClick={{ {handler_wrapper_name} }}')

        return lines
    
    def _find_function_end(self, lines: List[str], start: int) -> int:
        """Find the end line of a function."""
        brace_count = 0
        started = False
        
        for i in range(start, min(start + 100, len(lines))):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    started = True
                elif char == '}':
                    brace_count -= 1
            
            if started and brace_count == 0:
                return i
        
        return start + 20  # Fallback
    
    def _find_showNotification_definition(self, lines: List[str]) -> int:
        """Find the line where showNotification is defined."""
        for i, line in enumerate(lines):
            if 'const showNotification' in line or 'const showNotification =' in line:
                return i
        return -1
    
    def _find_hook_injection_point(self, lines: List[str]) -> int:
        """
        Find where to inject hook calls.
        Should be AFTER showNotification is defined and BEFORE any event handlers.
        """
        # First, find showNotification definition
        show_notif_line = self._find_showNotification_definition(lines)
        
        if show_notif_line == -1:
            # Fallback: look for useState declarations
            for i, line in enumerate(lines):
                if 'useState' in line:
                    return i + 1
            return -1
        
        # Find the end of showNotification function
        # It's usually a single-line or multi-line function
        brace_count = 0
        for i in range(show_notif_line, min(show_notif_line + 30, len(lines))):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
            
            # If we've closed all braces and found a semicolon, we're done
            if brace_count == 0 and ';' in line:
                return i + 1
        
        # Fallback: return line after showNotification
        return show_notif_line + 2
    
    def _inject_hook_calls_at_component_level(self, lines: List[str]) -> List[str]:
        """
        Inject hook calls at component level (after showNotification, before handlers).
        This fixes the TS2448/TS2454 errors.
        """
        print("  - Injecting hook calls at component level...")
        
        # Find injection point
        injection_point = self._find_hook_injection_point(lines)
        
        if injection_point == -1:
            print("    [WARNING] Could not find hook injection point, skipping...")
            return lines
        
        # Collect all hooks that need to be called
        hook_calls = []
        hook_calls.append("")
        hook_calls.append("  // Auto-generated hook calls (at component level)")
        
        # Find all screen_mappings that have hooks
        for screen in self.screen_mappings:
            story_id = screen.get('story_id', '')
            handler_mappings = screen.get('handler_mappings', [])
            
            if story_id and handler_mappings:
                # Generate hook name (same logic as in _generate_screen_hook)
                hook_name = f"use{self._normalize_name(story_id.replace(' ', ''))}Logic"
                
                # Extract handler function names
                handler_names = []
                for mapping in handler_mappings:
                    func_name = mapping.get('tsx_function_name', '')
                    if func_name:
                        handler_names.append(func_name)
                
                if handler_names:
                    # Generate hook call with destructuring (no aliasing needed)
                    destructured = ', '.join(handler_names)
                    hook_calls.append(f"  const {{ {destructured} }} = {hook_name}(showNotification);")
        
        hook_calls.append("")
        
        # Insert hook calls at the injection point
        lines = lines[:injection_point] + hook_calls + lines[injection_point:]
        
        print(f"    ✓ Injected {len(hook_calls) - 3} hook call(s) at line {injection_point}")
        
        return lines
    
    def _add_api_data_loading(self, lines: List[str]) -> List[str]:
        """Add useEffect for loading data from APIs."""
        print("  - Adding API data loading...")
        
        # Find the component function start
        component_start = -1
        for i, line in enumerate(lines):
            if 'const ' in line and '= () =>' in line and 'Screen' not in line:
                # This is likely the main component
                if '{' in line or (i + 1 < len(lines) and '{' in lines[i + 1]):
                    component_start = i
                    break
        
        if component_start == -1:
            return lines
        
        # Find where to insert useEffect (after useState declarations)
        insert_point = component_start + 1
        for i in range(component_start + 1, min(component_start + 50, len(lines))):
            if 'useState' in lines[i]:
                insert_point = i + 1
        
        # Build useEffect for data loading
        useeffect_code = [
            "",
            "  // Load initial data from API",
            "  useEffect(() => {",
            "    const loadData = async () => {",
            "      try {",
        ]
        
        # Add API calls for main entities used in screens
        entities_to_load = set()
        for screen in self.screen_mappings:
            entity = screen.get('primary_entity', '')
            if entity:
                entities_to_load.add(entity)
        
        for entity in entities_to_load:
            service_name = f"{self._normalize_name(entity)}Service"
            # Assume there's a state variable for this entity
            var_name = f"{self._to_camel_case(entity)}Items"
            setter_name = f"set{self._normalize_name(entity)}Items"
            
            useeffect_code.append(f"        // const data = await {service_name}.getAll();")
            useeffect_code.append(f"        // {setter_name}(data);")
        
        useeffect_code.extend([
            "      } catch (error) {",
            "        console.error('Failed to load data:', error);",
            "      }",
            "    };",
            "    loadData();",
            "  }, []);",
            "",
        ])
        
        # Insert useEffect
        lines = lines[:insert_point] + useeffect_code + lines[insert_point:]
        
        # Make sure useEffect is imported
        for i, line in enumerate(lines):
            if "import React" in line and "useEffect" not in line:
                if "{ useState" in line:
                    lines[i] = line.replace("{ useState", "{ useState, useEffect")
                elif "{useState" in line:
                    lines[i] = line.replace("{useState", "{useState, useEffect")
                break
        
        return lines
    
    def _fix_typescript_types(self, content: str) -> str:
        """Fix TypeScript type issues with smart element type detection."""
        lines = content.splitlines()
        fixed_lines = []
        in_select = False
        
        for i, line in enumerate(lines):
            # Track if we're inside a <select> element
            if '<select' in line:
                in_select = True
            
            # Fix onChange handlers based on context
            if 'onChange=' in line:
                if in_select:
                    # Fix select elements - replace any Input type with Select type
                    line = re.sub(
                        r'onChange=\{\(e: React\.ChangeEvent<HTMLInputElement>\)',
                        r'onChange={(e: React.ChangeEvent<HTMLSelectElement>)',
                        line
                    )
                    # Also add types if missing
                    line = re.sub(
                        r'onChange=\{\(e\)\s*=>',
                        r'onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>',
                        line
                    )
                elif '<input' in line or (i > 0 and '<input' in lines[i-1]):
                    # Fix input elements
                    line = re.sub(
                        r'onChange=\{\(e\)\s*=>',
                        r'onChange={(e: React.ChangeEvent<HTMLInputElement>) =>',
                        line
                    )
                elif '<textarea' in line or (i > 0 and '<textarea' in lines[i-1]):
                    # Fix textarea elements
                    line = re.sub(
                        r'onChange=\{\(e\)\s*=>',
                        r'onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>',
                        line
                    )
            
            # Track when we exit the select element
            if in_select and '/>' in line:
                in_select = False
            if in_select and '</select>' in line:
                in_select = False
            
            fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        # Add type annotations to common patterns
        replacements = [
            (r'showNotification\s*=\s*\((\w+),\s*(\w+)\)', r'showNotification = (\1: string, \2: string)'),
            (r'showModal\s*=\s*\((\w+)\)', r'showModal = (\1: string)'),
            (r'showScreen\s*=\s*\((\w+)\)', r'showScreen = (\1: string)'),
            (r'filter\(item =>', r'filter((item: any) =>'),
            (r'map\(\(item, index\)', r'map((item: any, index: number)'),
            (r'onClick=\{\(e\) =>', r'onClick={(e: React.MouseEvent) =>'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        return content


def main():
    """Main entry point."""
    if len(sys.argv) < 6:
        print("Usage: python step_08_frontend_generator_claude_llm.py <wired_ui.json> <input_tsx> <input_dir> <output_dir> <tsx_metadata.json>")
        print("\nArguments:")
        print("  wired_ui.json     - Wiring plan generated by Step 07")
        print("  input_tsx         - Original TSX file to wire (can be same as in input_dir)")
        print("  input_dir         - Directory containing source files")
        print("  output_dir        - Directory to write generated output")
        print("  tsx_metadata.json - TSX metadata from Step 06 (for ID injection)")
        print("\nExample:")
        print("  python step_08_frontend_generator_claude_llm.py wired_ui.json ui_react_component.tsx . ./output tsx_metadata.json")
        sys.exit(1)
    
    wired_ui_path = Path(sys.argv[1])
    input_tsx_path = Path(sys.argv[2])
    input_dir = Path(sys.argv[3])
    output_dir = Path(sys.argv[4])
    tsx_metadata_path = Path(sys.argv[5])
    
    # Validate inputs
    if not wired_ui_path.exists():
        print(f"[ERROR] Wiring plan not found: {wired_ui_path}")
        sys.exit(1)
    
    if not input_tsx_path.exists():
        print(f"[ERROR] Input TSX file not found: {input_tsx_path}")
        sys.exit(1)
    
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        sys.exit(1)
    
    if not tsx_metadata_path.exists():
        print(f"[WARNING] TSX metadata not found: {tsx_metadata_path}")
        print(f"[WARNING] ID injection will be skipped")
        tsx_metadata_path = None  # Set to None to handle gracefully
    
    print(f"--- Step 08: Frontend Code Generation ---")
    print(f"Wiring Plan: {wired_ui_path}")
    print(f"Input TSX: {input_tsx_path}")
    print(f"Input Dir: {input_dir}")
    print(f"Output Dir: {output_dir}")
    print(f"TSX Metadata: {tsx_metadata_path if tsx_metadata_path else 'None (ID injection disabled)'}")
    
    # Load wiring plan
    with open(wired_ui_path, 'r', encoding='utf-8') as f:
        wiring_plan = json.load(f)
    
    # Validate wiring plan format
    if 'screen_mappings' not in wiring_plan and 'stories' in wiring_plan:
        print("[WARNING] Detected OLD wiring plan format (stories[]). Expected NEW format (screen_mappings[]).")
        print("[WARNING] Please regenerate wiring plan using Step 06 and Step 07.")
        sys.exit(1)
    
    # Copy input TSX to input_dir if different location
    if input_tsx_path.parent != input_dir:
        import shutil
        dest_tsx = input_dir / input_tsx_path.name
        if not dest_tsx.exists():
            shutil.copy(input_tsx_path, dest_tsx)
            print(f"[INFO] Copied TSX to input directory: {dest_tsx}")
    
    # Generate code
    generator = FrontendCodeGenerator(
        wiring_plan=wiring_plan,
        input_dir=input_dir,
        output_dir=output_dir,
        tsx_metadata_path=tsx_metadata_path
    )
    
    generator.generate()
    
    print(f"\n{'='*60}")
    print(f"[SUCCESS] Frontend code generation complete!")
    print(f"{'='*60}")
    print(f"\nGenerated files in: {output_dir}")
    print(f"\nNext steps:")
    print(f"  1. cd {output_dir}")
    print(f"  2. npm install")
    print(f"  3. npm start")
    print(f"\nEnsure backend API is running at http://localhost:8000")


if __name__ == '__main__':
    main()
