"""
RAG-Enhanced Analyzer for UI Component Analysis
This module provides RAG (Retrieval-Augmented Generation) capabilities to enhance
LLM analysis with fine-tuning data context without requiring model fine-tuning.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

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


@dataclass
class RAGContext:
    """Holds retrieved context for RAG enhancement"""
    business_terms: List[Dict[str, str]]
    similar_examples: List[Dict[str, Any]]
    relevance_score: float
    context_summary: str


class BusinessTerminologyRAG:
    """RAG system for business terminology and context retrieval"""
    
    def __init__(self, fine_tuning_data_folder: str):
        """Initialize RAG system with fine-tuning data"""
        self.fine_tuning_folder = Path(fine_tuning_data_folder)
        self.business_context = {}
        self.fine_tuning_examples = []
        self.vectorizer = None
        self.term_vectors = None
        self.example_vectors = None
        
        # Load data
        self._load_business_context()
        self._load_fine_tuning_examples()
        self._build_vector_index()
    
    def _load_business_context(self):
        """Load business context from JSON file"""
        context_file = self.fine_tuning_folder / "business_context.json"
        
        if context_file.exists():
            with open(context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.business_context = data.get('terminology', {})
                print(f"Loaded {len(self.business_context)} business terms")
        else:
            print("Business context file not found")
    
    def _load_fine_tuning_examples(self):
        """Load fine-tuning examples from JSONL file"""
        # Try multiple possible locations and filenames
        possible_files = [
        #    self.fine_tuning_folder / "costco_fine_tuning_data.jsonl",
        #    self.fine_tuning_folder.parent / "Fine-Tuning-data" / "business_context.json",
            self.fine_tuning_folder.parent / "Fine-Tuning-data" / "costco_terminology_complete_context.jsonl"
        ]
        
        for jsonl_file in possible_files:
            if jsonl_file.exists():
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            example = json.loads(line.strip())
                            self.fine_tuning_examples.append(example)
                        except json.JSONDecodeError:
                            continue
                print(f"Loaded {len(self.fine_tuning_examples)} fine-tuning examples from {jsonl_file.name}")
                return
        
        print("Fine-tuning data file not found in any location")
    
    def _build_vector_index(self):
        """Build vector index for similarity search"""
        if not self.business_context and not self.fine_tuning_examples:
            print("No data to build vector index")
            return
        
        # Prepare text corpus for vectorization
        all_texts = []
        
        # Add business terms and definitions
        for term, definition in self.business_context.items():
            all_texts.append(f"{term} {definition}")
        
        # Add fine-tuning examples
        for example in self.fine_tuning_examples:
            messages = example.get('messages', [])
            text_parts = []
            for msg in messages:
                if msg.get('role') in ['user', 'assistant']:
                    text_parts.append(msg.get('content', ''))
            all_texts.append(' '.join(text_parts))
        
        if all_texts:
            # Create TF-IDF vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2),
                lowercase=True
            )
            
            # Fit and transform texts
            self.term_vectors = self.vectorizer.fit_transform(all_texts)
            print(f"Built vector index with {len(all_texts)} documents")
    
    def retrieve_relevant_context(self, query: str, top_k: int = 5) -> RAGContext:
        """Retrieve relevant context for a given query"""
        
        if not self.vectorizer or self.term_vectors is None:
            return RAGContext([], [], 0.0, "No context available")
        
        # Vectorize query
        query_vector = self.vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.term_vectors).flatten()
        
        # Get top-k most similar indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Extract relevant business terms
        relevant_terms = []
        similar_examples = []
        
        term_count = len(self.business_context)
        
        # First add exact matches
        exact_matches = self._find_exact_term_matches(query)
        relevant_terms.extend(exact_matches)
        existing_terms = {term['term'] for term in exact_matches}
        
        for idx in top_indices:
            if similarities[idx] > 0.05:  # Lower threshold for better recall
                if idx < term_count:
                    # It's a business term
                    term_list = list(self.business_context.items())
                    term, definition = term_list[idx]
                    # Avoid duplicates from exact matching
                    if term not in existing_terms:
                        relevant_terms.append({
                            'term': term,
                            'definition': definition,
                            'relevance': float(similarities[idx])
                        })
                else:
                    # It's a fine-tuning example
                    example_idx = idx - term_count
                    if example_idx < len(self.fine_tuning_examples):
                        example = self.fine_tuning_examples[example_idx]
                        similar_examples.append({
                            'example': example,
                            'relevance': float(similarities[idx])
                        })
        
        # Calculate overall relevance
        avg_relevance = np.mean(similarities[top_indices]) if len(top_indices) > 0 else 0.0
        
        # Debug: Print what was found
        print(f"RAG Results - Found {len(relevant_terms)} terms, {len(similar_examples)} examples, avg relevance: {avg_relevance:.3f}")
        if relevant_terms:
            print(f"Top business terms found: {[t['term'] for t in relevant_terms[:3]]}")
        
        # Create context summary
        context_summary = self._create_context_summary(relevant_terms, similar_examples)
        
        return RAGContext(
            business_terms=relevant_terms,
            similar_examples=similar_examples,
            relevance_score=float(avg_relevance),
            context_summary=context_summary
        )
    
    def _create_context_summary(self, terms: List[Dict], examples: List[Dict]) -> str:
        """Create a summary of retrieved context"""
        summary_parts = []
        
        if terms:
            summary_parts.append("**Relevant Business Terms:**")
            for term in terms[:3]:  # Top 3 terms
                summary_parts.append(f"- **{term['term']}**: {term['definition']}")
        
        if examples:
            summary_parts.append("\n**Similar Context Examples:**")
            for i, example in enumerate(examples[:2], 1):  # Top 2 examples
                messages = example['example'].get('messages', [])
                user_msg = next((m['content'] for m in messages if m.get('role') == 'user'), '')
                assistant_msg = next((m['content'] for m in messages if m.get('role') == 'assistant'), '')
                
                if user_msg and assistant_msg:
                    summary_parts.append(f"{i}. Q: {user_msg[:100]}...")
                    summary_parts.append(f"   A: {assistant_msg[:150]}...")
        
        return '\n'.join(summary_parts) if summary_parts else "No relevant context found"
    
    def get_business_term_definition(self, term: str) -> Optional[str]:
        """Get definition for a specific business term"""
        # Exact match first
        if term in self.business_context:
            return self.business_context[term]
        
        # Case-insensitive match
        for key, value in self.business_context.items():
            if key.lower() == term.lower():
                return value
        
        # Partial match
        term_lower = term.lower()
        for key, value in self.business_context.items():
            if term_lower in key.lower() or key.lower() in term_lower:
                return value
        
        return None
    
    def _find_exact_term_matches(self, query: str) -> List[Dict]:
        """Find exact matches for business terms in the query"""
        exact_matches = []
        query_upper = query.upper()
        
        for term, definition in self.business_context.items():
            # Check for exact term matches (case insensitive)
            if term.upper() in query_upper:
                exact_matches.append({
                    'term': term,
                    'definition': definition,
                    'relevance': 1.0  # Highest relevance for exact matches
                })
        
        return exact_matches


class RAGEnhancedUIAnalyzer:
    """Enhanced UI Component Analyzer with RAG capabilities"""
    
    def __init__(self, openai_client, deployment_name: str, fine_tuning_data_folder: str, api_key: Optional[str] = None):
        """Initialize with OpenAI client and RAG system"""
        print("\n Initializing RAG-Enhanced UI Component Analyzer")
        print("=" * 50)
        
        # Get API key from Key Vault if not provided
        if not api_key:
            api_key = get_azure_openai_api_key_from_keyvault()
            if not api_key:
                # Fallback to environment variable
                api_key = os.getenv("AZURE_OPENAI_API_KEY")
                print("API Key Source: Environment Variable (.env file)")
        
        print(f"\nRAG Configuration:")
        print(f"   • Deployment: {deployment_name}")
        print(f"   • API Key: {'Available' if api_key else 'Missing'}")
        print(f"   • Fine-tuning Data: {fine_tuning_data_folder}")
        
        self.client = openai_client
        self.deployment_name = deployment_name
        self.api_key = api_key
        self.rag_system = BusinessTerminologyRAG(fine_tuning_data_folder)
        
        # Add caching for LLM descriptions to avoid redundant calls
        self._description_cache = {}
        
        print(f"\nRAG Analyzer Ready (API Key from {'Key Vault' if api_key != os.getenv('AZURE_OPENAI_API_KEY') else 'Environment'})")
        
    def enhance_analysis_with_rag(self, 
                                 component_content: str, 
                                 base_analysis: Any,
                                 analysis_context: str = "") -> Any:
        """Enhance analysis using RAG-retrieved context"""
        
        # Create query from component content and context
        query = self._create_rag_query(component_content, analysis_context)
        
        # Retrieve relevant context
        rag_context = self.rag_system.retrieve_relevant_context(query, top_k=5)
        
        # Enhance the prompt with RAG context
        enhanced_prompt = self._create_rag_enhanced_prompt(
            component_content, 
            base_analysis, 
            rag_context
        )
        
        # Call LLM with enhanced prompt
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert UI component analyzer with deep knowledge of business terminology and processes. Use the provided business context to enhance your analysis."
                    },
                    {
                        "role": "user",
                        "content": enhanced_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=6000
            )
            
            # Process the response
            enhanced_analysis = self._process_llm_response(response, base_analysis, rag_context)
            
            print(f"RAG Enhancement completed (relevance: {rag_context.relevance_score:.2f})")
            return enhanced_analysis
            
        except Exception as e:
            print(f"RAG Enhancement failed: {str(e)}")
            return base_analysis
    
    def _create_rag_query(self, component_content: str, context: str) -> str:
        """Create a query for RAG retrieval"""
        # Extract key terms from component content
        key_terms = []
        
        # Look for business-related terms in the content
        business_patterns = [
            r'\b(?:RTV|NSI|BOL|POS|Account|Vendor|Shipment|Disposition|Workflow)\b',
            r'\b(?:inventory|return|salvage|destroy|tracking|approval)\b',
            r'\b(?:worklist|process|maintenance|entry|document)\b'
        ]
        
        for pattern in business_patterns:
            matches = re.findall(pattern, component_content, re.IGNORECASE)
            key_terms.extend(matches)
        
        # Debug: Print found terms
        print(f"RAG Query - Found key terms: {key_terms[:10]}")
        
        # Combine with context
        query_parts = [context] if context else []
        query_parts.extend(key_terms[:10])  # Limit to avoid very long queries
        
        return ' '.join(query_parts)
    

    
    def _create_rag_enhanced_prompt(self, 
                                   component_content: str, 
                                   base_analysis: Any, 
                                   rag_context: RAGContext) -> str:
        """Create enhanced prompt with RAG context"""
        
        prompt = f"""
You are analyzing a UI component for business context. Based on the business terminology provided, give clear and structured insights.

**BUSINESS CONTEXT AVAILABLE:**
{rag_context.context_summary}

**COMPONENT CODE:**
```
{component_content[:2500]}
```

**ANALYSIS INSTRUCTIONS:**

1. **IDENTIFY BUSINESS TERMS**: Find business terms from the context that appear in the component code (like RTV, NSI, BOL, workflow, disposition, etc.)

2. **DESCRIBE WORKFLOWS**: Identify complete business processes this UI supports. Write each workflow as a clear, complete sentence.

3. **BUSINESS INSIGHTS**: Explain how this component serves business operations and user goals.

**OUTPUT FORMAT:**
Provide a structured analysis with clear sections:

### Business Terms Found:
[List each term with its business purpose in this context]

### Business Workflows Supported:
[Complete sentences describing each workflow process]

### Component Business Purpose:
[Clear explanation of business value]

### User Experience Considerations:
[Practical suggestions for business users]

Keep responses clear and business-focused. Avoid technical jargon.
"""
        return prompt
    
    def _safe_serialize_analysis(self, analysis: Any) -> str:
        """Safely serialize analysis object for prompt inclusion"""
        try:
            if hasattr(analysis, '__dict__'):
                # Convert to dict and handle nested objects
                data = {}
                for key, value in analysis.__dict__.items():
                    if hasattr(value, '__dict__'):
                        # Nested object - convert to dict
                        data[key] = str(value)  # Simple string representation
                    elif isinstance(value, list):
                        # List - limit length and stringify complex objects
                        data[key] = [str(item) if hasattr(item, '__dict__') else item for item in value[:5]]
                    else:
                        data[key] = value
                return json.dumps(data, indent=2, default=str)
            else:
                return str(analysis)
        except Exception as e:
            return f"Analysis summary: {type(analysis).__name__} with {len(getattr(analysis, '__dict__', {}))} attributes"
    
    def _process_llm_response(self, response, base_analysis: Any, rag_context: RAGContext) -> Any:
        """Process LLM response and integrate with base analysis"""
        
        try:
            # Extract content from response
            enhanced_content = response.choices[0].message.content
            
            # Try to parse as JSON first
            if enhanced_content.strip().startswith('{'):
                try:
                    enhanced_data = json.loads(enhanced_content)
                    # Merge with base analysis
                    return self._merge_analyses(base_analysis, enhanced_data, rag_context)
                except json.JSONDecodeError:
                    pass
            
            # If not JSON, extract insights and apply to base analysis
            return self._extract_insights_and_apply(base_analysis, enhanced_content, rag_context)
            
        except Exception as e:
            print(f"Error processing LLM response: {str(e)}")
            return base_analysis
    
    def _merge_analyses(self, base_analysis: Any, enhanced_data: Dict, rag_context: RAGContext) -> Any:
        """Merge enhanced data with base analysis"""
        
        # Create a deep copy of base analysis to modify
        import copy
        enhanced_analysis = copy.deepcopy(base_analysis)
        
        try:
            # Enhance screens with business context
            if hasattr(enhanced_analysis, 'screens') and 'screens' in enhanced_data:
                enhanced_screens = enhanced_data.get('screens', [])
                
                for i, screen in enumerate(enhanced_analysis.screens):
                    if i < len(enhanced_screens):
                        enhanced_screen_data = enhanced_screens[i]
                        
                        # Update screen description with business context
                        if 'description' in enhanced_screen_data:
                            screen.description = enhanced_screen_data['description']
                        
                        # Add business context to screen
                        if not hasattr(screen, 'business_context'):
                            screen.business_context = {}
                        
                        # Extract business insights
                        screen.business_context.update({
                            'rag_enhanced': True,
                            'business_terms_found': [term['term'] for term in rag_context.business_terms],
                            'relevance_score': rag_context.relevance_score
                        })
                        
                        # Enhance elements if provided
                        if 'elements' in enhanced_screen_data and hasattr(screen, 'elements'):
                            enhanced_elements = enhanced_screen_data.get('elements', [])
                            
                            for j, element in enumerate(screen.elements):
                                if j < len(enhanced_elements):
                                    enhanced_element = enhanced_elements[j]
                                    
                                    # Update descriptions with business context
                                    if 'description' in enhanced_element:
                                        if not hasattr(element, 'business_description'):
                                            element.business_description = enhanced_element['description']
                                    
                                    # Add business context to element
                                    if 'business_purpose' in enhanced_element:
                                        if not hasattr(element, 'business_purpose'):
                                            element.business_purpose = enhanced_element['business_purpose']
            
            # Add global RAG metadata
            enhanced_analysis.rag_metadata = {
                'relevance_score': rag_context.relevance_score,
                'business_terms_used': len(rag_context.business_terms),
                'context_applied': True,
                'enhancement_timestamp': str(json.dumps(None, default=str))  # Current timestamp
            }
            
            return enhanced_analysis
            
        except Exception as e:
            print(f"Error merging analyses: {str(e)}")
            # Fall back to insights extraction
            return self._extract_insights_and_apply(base_analysis, str(enhanced_data), rag_context)
    
    def _extract_insights_and_apply(self, base_analysis: Any, enhanced_content: str, rag_context: RAGContext) -> Any:
        """Extract insights from text response and apply to base analysis"""
        
        # Create a deep copy to modify
        import copy
        enhanced_analysis = copy.deepcopy(base_analysis)
        
        # Look for specific enhancements in the text
        insights = {
            'business_terms_identified': [],
            'process_workflows': [],
            'enhancement_suggestions': [],
            'rag_applied': True
        }
        
        # Extract business terms mentioned
        for term in rag_context.business_terms:
            if term['term'].lower() in enhanced_content.lower():
                insights['business_terms_identified'].append({
                    'term': term['term'],
                    'definition': term['definition'],
                    'relevance': term['relevance']
                })
        
        # Extract workflow processes - improved to get clean, complete descriptions
        workflow_processes = []
        
        # Generate clean workflows using LLM based on RAG context
        if rag_context and rag_context.business_terms:
            workflow_processes = self._generate_clean_workflows(rag_context, enhanced_content)
        
        # If LLM workflow generation fails, fall back to improved extraction
        if not workflow_processes:
            workflow_processes = self._extract_workflows_from_content(enhanced_content)
        
        # If no structured workflows found, fall back to sentence extraction
        if not workflow_processes:
            workflow_keywords = ['workflow', 'process', 'processing', 'maintenance', 'disposition', 'approval', 'RTV', 'NSI']
            fallback_sentences = re.split(r'[.!?]+', enhanced_content)
            
            for sentence in fallback_sentences:
                sentence = sentence.strip()
                if len(sentence) > 30:  # Longer minimum for quality
                    for keyword in workflow_keywords:
                        if keyword.lower() in sentence.lower():
                            clean_sentence = re.sub(r'\s+', ' ', sentence).strip()
                            if clean_sentence and clean_sentence not in workflow_processes:
                                workflow_processes.append(clean_sentence)
                            break
        
        # Remove duplicates and limit to top 8 (increased from 5)
        insights['process_workflows'] = list(dict.fromkeys(workflow_processes))[:8]
        
        # Extract enhancement suggestions - improved to get complete suggestions
        suggestion_sentences = []
        suggestion_keywords = ['suggest', 'recommend', 'consider', 'improve', 'enhance', 'add', 'include']
        
        # Split content for suggestions extraction
        suggestion_content_sentences = re.split(r'[.!?]+', enhanced_content)
        
        for sentence in suggestion_content_sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:
                for keyword in suggestion_keywords:
                    if keyword.lower() in sentence.lower() and ('could' in sentence.lower() or 'should' in sentence.lower() or 'would' in sentence.lower()):
                        clean_sentence = re.sub(r'\s+', ' ', sentence).strip()
                        if clean_sentence and len(clean_sentence) > 30:
                            suggestion_sentences.append(clean_sentence)
                        break
        
        insights['enhancement_suggestions'] = list(dict.fromkeys(suggestion_sentences))[:3]
        
        # Apply insights to analysis structure
        enhanced_analysis.rag_enhancements = insights
        
        # Create a global business glossary to avoid repetition
        business_glossary = {}
        for term_info in insights['business_terms_identified']:
            business_glossary[term_info['term']] = term_info['definition']
        
        # Create standardized business context templates to avoid duplication
        business_templates = self._create_business_templates(rag_context)
        
        # Add comprehensive business context to screens and elements
        if hasattr(enhanced_analysis, 'screens'):
            for i, screen in enumerate(enhanced_analysis.screens):
                # Analyze screen for business context
                screen_text = f"{screen.name} {getattr(screen, 'description', '')}".lower()
                screen_specific_terms = []
                screen_workflows = []
                
                # Find business terms specific to this screen
                for term_info in insights['business_terms_identified']:
                    if term_info['term'].lower() in screen_text:
                        screen_specific_terms.append(term_info['term'])
                
                # Find workflows specific to this screen
                for workflow in insights['process_workflows']:
                    if any(word in workflow.lower() for word in screen.name.lower().split()):
                        screen_workflows.append(workflow)
                
                # Add standardized business context for screen
                screen_business_info = self._get_standardized_screen_business_context(
                    screen, screen_specific_terms, screen_workflows, business_templates
                )
                
                # Apply standardized structure to screen
                self._set_attribute_safe(screen, 'business_context', screen_business_info)
                
                # Enhance elements with standardized business context (avoid duplication)
                if hasattr(screen, 'elements'):
                    processed_element_types = set()  # Track processed types to avoid duplication
                    
                    for element in screen.elements:
                        element_key = f"{element.element_type}_{getattr(element, 'label', '')}_{getattr(element, 'text_content', '')}"
                        
                        # Only add business context if this element type/purpose hasn't been processed
                        if element_key not in processed_element_types:
                            # Use rich business context from RAG data
                            element_business_context = self._create_rich_element_business_context(
                                element, rag_context, screen_specific_terms
                            )
                            if element_business_context:
                                self._set_attribute_safe(element, 'business_context', element_business_context)
                                processed_element_types.add(element_key)
        
        # Enhance global functions with business context
        if hasattr(enhanced_analysis, 'global_functions'):
            for func in enhanced_analysis.global_functions:
                func_business_context = self._determine_function_business_context(func, rag_context)
                if func_business_context:
                    self._set_attribute_safe(func, 'business_value', func_business_context)
        
        # Enhance global state variables with business context
        if hasattr(enhanced_analysis, 'global_state'):
            for state_var in enhanced_analysis.global_state:
                state_business_context = self._determine_state_business_context(state_var, rag_context)
                if state_business_context:
                    self._set_attribute_safe(state_var, 'business_value', state_business_context)
                
                # Enhance element descriptions with business context
                if hasattr(screen, 'elements'):
                    for element in screen.elements:
                        # Add business purpose based on element type and label
                        element_text = f"{element.element_type} {getattr(element, 'label', '')} {getattr(element, 'text_content', '')}".lower()
                        
                        # Find matching business terms
                        matching_terms = []
                        for term_info in insights['business_terms_identified']:
                            if term_info['term'].lower() in element_text:
                                matching_terms.append(term_info)
                        
                        if matching_terms and not hasattr(element, 'business_context'):
                            element.business_context = {
                                'related_terms': matching_terms,
                                'rag_enhanced': True
                            }
        
        # Add global RAG metadata with timestamp and business glossary
        import datetime
        enhanced_analysis.rag_metadata = {
            'relevance_score': rag_context.relevance_score,
            'business_terms_used': len(rag_context.business_terms),
            'context_applied': True,
            'enhancement_timestamp': datetime.datetime.now().isoformat(),
            'total_insights': len(insights['business_terms_identified']) + len(insights['process_workflows'])
        }
        
        # Add a clean business glossary (separate from repetitive screen context)
        enhanced_analysis.business_glossary = business_glossary
        
        print(f"Applied {len(insights['business_terms_identified'])} business terms to analysis")
        print(f"Extracted {len(insights['process_workflows'])} workflow processes")
        
        return enhanced_analysis
    
    def _generate_clean_workflows(self, rag_context, enhanced_content):
        """Generate clean workflow descriptions using LLM and RAG context"""
        try:
            # Get business context from RAG system
            business_context_summary = ""
            if rag_context and rag_context.business_terms:
                business_context_summary = "\n".join([
                    f"- {term['term']}: {term['definition']}" 
                    for term in rag_context.business_terms[:5]
                ])
            
            # Create LLM prompt for clean workflow generation
            prompt = f"""Based on the business context and UI analysis provided, generate clean business workflow descriptions.

**BUSINESS CONTEXT:**
{business_context_summary}

**UI ANALYSIS CONTENT:**
{enhanced_content[:1500]}

**TASK:**
Generate 3-5 clear, complete business workflow descriptions that this UI supports.

**REQUIREMENTS:**
- Each workflow should be a complete, standalone sentence
- Focus on business processes, not technical details
- Use business terminology from the context
- Make descriptions specific and actionable
- Avoid incomplete sentences or fragments
- No markdown formatting or special characters

**OUTPUT FORMAT:**
Return only a JSON array of workflow descriptions:
["workflow description 1", "workflow description 2", "workflow description 3"]

Example:
["NSI item entry and tracking workflow", "Return to vendor processing workflow", "Disposition decision and approval workflow"]"""

            # Call LLM to generate clean workflows
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business process analyst who specializes in identifying and describing business workflows from UI analysis. Generate clear, complete workflow descriptions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=400
            )
            
            # Parse LLM response
            llm_content = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            if llm_content.startswith('[') and llm_content.endswith(']'):
                try:
                    workflows = json.loads(llm_content)
                    if isinstance(workflows, list):
                        print(f"Generated {len(workflows)} clean workflow descriptions")
                        return workflows[:5]  # Limit to 5
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Extract lines from text
            lines = [line.strip() for line in llm_content.split('\n') if line.strip()]
            clean_workflows = []
            for line in lines:
                # Remove quotes and list markers
                clean_line = re.sub(r'^["\']*[\d\-\*\.\)]*\s*', '', line)
                clean_line = clean_line.strip('"\'.,').strip()
                if len(clean_line) > 20 and clean_line not in clean_workflows:
                    clean_workflows.append(clean_line)
            
            print(f"Extracted {len(clean_workflows)} workflow descriptions from text")
            return clean_workflows[:5]
            
        except Exception as e:
            print(f"Error generating clean workflows: {str(e)}")
            return []
    
    def _extract_workflows_from_content(self, enhanced_content):
        """Fallback method to extract workflows from content when LLM fails"""
        workflow_processes = []
        
        # Look for complete sentences mentioning workflow concepts
        sentences = re.split(r'[.!?]+', enhanced_content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            # Clean up sentence - remove markdown and formatting
            clean_sentence = re.sub(r'\*+', '', sentence)  # Remove asterisks
            clean_sentence = re.sub(r'\s+', ' ', clean_sentence).strip()
            
            # Check if it's a meaningful workflow description
            if (len(clean_sentence) > 30 and 
                any(keyword in clean_sentence.lower() for keyword in 
                    ['workflow', 'process', 'disposition', 'approval', 'management', 'tracking']) and
                not clean_sentence.startswith(('Business', 'Component', 'User Experience', 'The system'))):
                
                # Ensure it ends properly
                if not clean_sentence.endswith('.'):
                    clean_sentence += '.'
                
                if clean_sentence not in workflow_processes:
                    workflow_processes.append(clean_sentence)
        
        # If still no good workflows, create some based on common patterns
        if not workflow_processes:
            workflow_processes = [
                "Item entry and tracking workflow for business operations",
                "Data validation and processing workflow",
                "Business approval and authorization workflow"
            ]
        
        return workflow_processes[:5]  # Limit to 5
    
    def _determine_business_value_for_screen(self, screen, screen_terms, rag_context):
        """Determine business value based on screen type and context - generic approach"""
        screen_name = screen.name.lower()
        screen_desc = getattr(screen, 'description', '').lower()
        
        business_value = {}
        
        # Extract purpose from business context and screen name patterns
        purpose_keywords = self._extract_purpose_keywords(screen_name, screen_desc, screen_terms)
        
        # Generate dynamic business value using LLM and RAG context
        business_value = self._generate_dynamic_business_value(screen, screen_terms, rag_context)
        
        # Add dynamic context from business terms
        if screen_terms:
            business_value['related_business_concepts'] = screen_terms
            business_value['domain_context'] = self._get_domain_context_from_terms(screen_terms, rag_context)
        
        # Add purpose keywords extracted from context
        if purpose_keywords:
            business_value['key_functions'] = purpose_keywords
        
        return business_value
    
    def _generate_dynamic_business_value(self, screen, screen_terms, rag_context):
        """Generate dynamic business value using LLM and Fine-Tuning-data context"""
        try:
            # Prepare context for LLM
            screen_name = getattr(screen, 'name', '')
            screen_desc = getattr(screen, 'description', '')
            
            # Get business context from RAG system
            business_context_summary = ""
            if rag_context and rag_context.business_terms:
                business_context_summary = "\n".join([
                    f"- {term['term']}: {term['definition']}" 
                    for term in rag_context.business_terms[:5]
                ])
            
            # Create LLM prompt for dynamic business value generation
            prompt = f"""Based on the business context and terminology provided, analyze this UI screen and generate appropriate business value descriptions.

**BUSINESS CONTEXT:**
{business_context_summary}

**SCREEN INFORMATION:**
- Screen Name: {screen_name}
- Screen Description: {screen_desc}
- Related Business Terms: {', '.join(screen_terms) if screen_terms else 'None identified'}

**TASK:**
Generate a business value analysis with these specific fields:
1. primary_purpose - What is the main business purpose of this screen?
2. functional_category - What category of business interface is this?
3. operational_role - What operational role does this screen serve?

**OUTPUT FORMAT:**
Return ONLY a valid JSON object with exactly these three fields:
{{
    "primary_purpose": "specific business purpose based on context",
    "functional_category": "appropriate business category",
    "operational_role": "operational role in business processes"
}}

Focus on the actual business domain and terminology provided. Be specific and relevant to the business context rather than generic."""

            # Call LLM to generate dynamic business value
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst expert who specializes in understanding UI screens within business contexts. Generate accurate, context-specific business value descriptions based on the provided business terminology and screen information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            # Parse LLM response
            llm_content = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            if llm_content.startswith('{') and llm_content.endswith('}'):
                try:
                    business_value = json.loads(llm_content)
                    print(f"Generated dynamic business value for screen: {screen_name}")
                    return business_value
                except json.JSONDecodeError as e:
                    print(f"JSON parse error for {screen_name}: {str(e)}")
            
            # Fallback: Extract values from text response
            business_value = self._extract_business_value_from_text(llm_content, screen_name)
            print(f"Extracted business value from text for screen: {screen_name}")
            return business_value
            
        except Exception as e:
            print(f"Error generating dynamic business value for {screen_name}: {str(e)}")
            # Return minimal fallback
            return self._get_fallback_business_value(screen, screen_terms)
    
    def _extract_business_value_from_text(self, llm_content, screen_name):
        """Extract business value fields from LLM text response"""
        business_value = {}
        
        # Try to extract specific fields from text
        lines = llm_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'primary_purpose' in line.lower():
                # Extract text after colon or quote
                match = re.search(r'[:"]([^"]+)', line)
                if match:
                    business_value['primary_purpose'] = match.group(1).strip(' ",')
            elif 'functional_category' in line.lower():
                match = re.search(r'[:"]([^"]+)', line)
                if match:
                    business_value['functional_category'] = match.group(1).strip(' ",')
            elif 'operational_role' in line.lower():
                match = re.search(r'[:"]([^"]+)', line)
                if match:
                    business_value['operational_role'] = match.group(1).strip(' ",')
        
        # Fill in missing fields with intelligent defaults
        if 'primary_purpose' not in business_value:
            business_value['primary_purpose'] = f"Business operations support for {screen_name}"
        if 'functional_category' not in business_value:
            business_value['functional_category'] = "Business Interface"
        if 'operational_role' not in business_value:
            business_value['operational_role'] = "Supports business process execution"
        
        return business_value
    
    def _get_fallback_business_value(self, screen, screen_terms):
        """Get minimal fallback business value when LLM fails"""
        screen_name = getattr(screen, 'name', 'Unknown')
        
        # Create basic business value with some intelligence
        if screen_terms:
            domain_hint = f"Related to {', '.join(screen_terms[:2])}"
            primary_purpose = f"Business operations involving {screen_terms[0]}" if screen_terms else "Business operations support"
        else:
            domain_hint = "General business operations"
            primary_purpose = f"Business functionality for {screen_name}"
        
        return {
            'primary_purpose': primary_purpose,
            'functional_category': 'Business Interface',
            'operational_role': f'Supports {domain_hint.lower()}'
        }
    
    def _determine_workflow_details_for_screen(self, screen, workflows, rag_context):
        """Determine workflow details based on screen context - generic approach"""
        screen_name = screen.name.lower()
        
        workflow_details = {
            'workflow_category': 'Generic Business Process',
            'process_type': self._classify_process_type(screen_name),
            'stage_in_lifecycle': self._determine_lifecycle_stage(screen_name, workflows)
        }
        
        # Extract workflow information from RAG context and business terms
        if workflows:
            workflow_details['identified_processes'] = workflows[:3]  # Limit to top 3
            workflow_details['process_insights'] = self._extract_process_insights(workflows)
        
        # Add dynamic workflow classification
        workflow_patterns = self._analyze_workflow_patterns(screen_name, rag_context)
        if workflow_patterns:
            workflow_details.update(workflow_patterns)
        
        return workflow_details
    
    def _determine_element_business_context(self, element, rag_context, screen_terms):
        """Determine business context for individual UI elements - generic approach"""
        element_type = getattr(element, 'element_type', '')
        element_label = getattr(element, 'label', '') or ''
        element_text = getattr(element, 'text_content', '') or ''
        
        element_context = element_label + ' ' + element_text
        element_context_lower = element_context.lower()
        
        business_context = {}
        
        # Generic element classification based on type and function
        element_function = self._classify_element_function(element_type, element_context_lower)
        
        if element_function:
            business_context = {
                'element_function': element_function,
                'business_purpose': self._get_generic_business_purpose(element_type, element_function),
                'operational_impact': self._get_operational_impact(element_type, element_function)
            }
        
        # Add business term context if found
        matching_terms = self._find_matching_business_terms(element_context_lower, rag_context.business_terms)
        if matching_terms:
            business_context['business_terminology'] = matching_terms
        
        return business_context if business_context else None
    
    def _classify_element_function(self, element_type, element_context):
        """Classify the function of an element based on content"""
        if element_type == 'button':
            if any(word in element_context for word in ['submit', 'save', 'process', 'execute']):
                return 'action_trigger'
            elif any(word in element_context for word in ['approve', 'authorize', 'confirm']):
                return 'authorization'
            elif any(word in element_context for word in ['review', 'view', 'show', 'display']):
                return 'information_access'
            else:
                return 'generic_action'
        
        elif element_type == 'input':
            if any(word in element_context for word in ['id', 'number', 'code', 'tracking']):
                return 'identifier_input'
            elif any(word in element_context for word in ['quantity', 'amount', 'count']):
                return 'numeric_input'
            elif any(word in element_context for word in ['date', 'time']):
                return 'temporal_input'
            else:
                return 'data_input'
        
        elif element_type == 'select':
            if any(word in element_context for word in ['status', 'state', 'stage']):
                return 'status_selection'
            elif any(word in element_context for word in ['type', 'category', 'class']):
                return 'classification'
            else:
                return 'option_selection'
        
        return 'generic_element'
    
    def _get_generic_business_purpose(self, element_type, element_function):
        """Get generic business purpose based on element function"""
        purposes = {
            'action_trigger': 'Initiates business process or transaction',
            'authorization': 'Provides control point for business approval',
            'information_access': 'Enables access to business information',
            'identifier_input': 'Captures unique business identifiers',
            'numeric_input': 'Records quantitative business data',
            'temporal_input': 'Captures time-sensitive business information',
            'data_input': 'Records business operational data',
            'status_selection': 'Manages business process state',
            'classification': 'Categorizes business entities',
            'option_selection': 'Selects from business-defined options',
            'generic_action': f'Supports {element_type}-based business operations',
            'generic_element': f'Provides {element_type} functionality for business use'
        }
        return purposes.get(element_function, f'Supports business operations through {element_type} interface')
    
    def _get_operational_impact(self, element_type, element_function):
        """Get operational impact based on element function"""
        impacts = {
            'action_trigger': 'Drives workflow progression and process completion',
            'authorization': 'Ensures compliance and proper business controls',
            'information_access': 'Supports informed decision making',
            'identifier_input': 'Enables precise tracking and audit capabilities',
            'numeric_input': 'Supports accurate business calculations and reporting',
            'temporal_input': 'Enables time-based business analytics',
            'data_input': 'Maintains business data integrity',
            'status_selection': 'Facilitates workflow management',
            'classification': 'Enables organized business data management',
            'option_selection': 'Standardizes business choices'
        }
        return impacts.get(element_function, 'Contributes to overall business process efficiency')
    
    def _find_matching_business_terms(self, element_context, business_terms):
        """Find business terms that match element context"""
        matches = []
        for term_info in business_terms:
            term_name = term_info.get('term', '').lower()
            if term_name in element_context:
                matches.append({
                    'term': term_info.get('term', ''),
                    'definition': term_info.get('definition', ''),
                    'relevance_score': term_info.get('relevance', 0)
                })
        return matches[:2]  # Limit to top 2 matches
    
    def _extract_purpose_keywords(self, screen_name, screen_desc, screen_terms):
        """Extract purpose keywords from screen context"""
        keywords = []
        
        # Extract from screen name
        name_parts = screen_name.replace('screen', '').split()
        keywords.extend([part for part in name_parts if len(part) > 2])
        
        # Extract from description
        if screen_desc:
            desc_words = screen_desc.split()
            keywords.extend([word for word in desc_words if len(word) > 3])
        
        # Extract from business terms
        keywords.extend(screen_terms)
        
        return list(set(keywords))[:5]  # Return unique keywords, max 5
    
    def _get_domain_context_from_terms(self, screen_terms, rag_context):
        """Extract domain context from business terms"""
        if not screen_terms:
            return "Generic business domain"
        
        # Look for domain indicators in business terms
        domain_keywords = []
        for term in screen_terms:
            term_lower = term.lower()
            if any(word in term_lower for word in ['inventory', 'stock', 'item']):
                domain_keywords.append('inventory_management')
            elif any(word in term_lower for word in ['return', 'vendor', 'supplier']):
                domain_keywords.append('vendor_relations')
            elif any(word in term_lower for word in ['maintenance', 'process', 'workflow']):
                domain_keywords.append('process_management')
        
        if domain_keywords:
            return f"Specialized for {', '.join(set(domain_keywords))}"
        return f"Business domain involving {', '.join(screen_terms)}"
    
    def _classify_process_type(self, screen_name):
        """Classify the type of business process"""
        if any(word in screen_name for word in ['dashboard', 'overview', 'summary']):
            return 'monitoring_process'
        elif any(word in screen_name for word in ['entry', 'input', 'create']):
            return 'data_entry_process'
        elif any(word in screen_name for word in ['maintenance', 'process', 'manage']):
            return 'operational_process'
        elif any(word in screen_name for word in ['inquiry', 'search', 'lookup']):
            return 'information_process'
        else:
            return 'business_process'
    
    def _determine_lifecycle_stage(self, screen_name, workflows):
        """Determine where this screen fits in the business lifecycle"""
        if any(word in screen_name for word in ['entry', 'create', 'new']):
            return 'initiation'
        elif any(word in screen_name for word in ['process', 'maintenance', 'manage']):
            return 'processing'
        elif any(word in screen_name for word in ['review', 'approve', 'validate']):
            return 'validation'
        elif any(word in screen_name for word in ['complete', 'finish', 'close']):
            return 'completion'
        elif any(word in screen_name for word in ['inquiry', 'search', 'view']):
            return 'information_access'
        else:
            return 'operational'
    
    def _extract_process_insights(self, workflows):
        """Extract insights from workflow descriptions"""
        insights = []
        for workflow in workflows:
            if len(workflow) > 50:  # Only meaningful workflows
                # Extract key action words
                action_words = []
                for word in workflow.split():
                    if word.lower() in ['process', 'review', 'approve', 'create', 'update', 'manage', 'track']:
                        action_words.append(word.lower())
                
                if action_words:
                    insights.append(f"Involves {', '.join(set(action_words))} operations")
        
        return insights[:3]  # Limit to top 3 insights
    
    def _analyze_workflow_patterns(self, screen_name, rag_context):
        """Analyze patterns in workflow based on screen context"""
        patterns = {}
        
        # Determine interaction complexity
        if any(word in screen_name for word in ['dashboard', 'overview']):
            patterns['interaction_complexity'] = 'high_level_monitoring'
        elif any(word in screen_name for word in ['entry', 'input']):
            patterns['interaction_complexity'] = 'detailed_data_entry'
        else:
            patterns['interaction_complexity'] = 'standard_operations'
        
        # Determine business criticality based on terms
        if rag_context.business_terms:
            patterns['business_criticality'] = 'domain_specific'
            patterns['domain_focus'] = [term.get('term', '') for term in rag_context.business_terms[:3]]
        else:
            patterns['business_criticality'] = 'standard_operations'
        
        return patterns
    
    def _determine_function_business_context(self, func, rag_context):
        """Determine business context for global functions - generic approach"""
        func_name = getattr(func, 'name', '').lower()
        
        # Classify function type generically
        func_category = self._classify_function_category(func_name)
        
        business_context = {
            'function_category': func_category,
            'business_purpose': self._get_function_business_purpose(func_category, func_name),
            'operational_role': self._get_function_operational_role(func_category)
        }
        
        # Add business term context if applicable
        matching_terms = self._find_matching_business_terms(func_name, rag_context.business_terms)
        if matching_terms:
            business_context['related_business_concepts'] = matching_terms
        
        return business_context
    
    def _classify_function_category(self, func_name):
        """Classify function into generic categories"""
        if any(word in func_name for word in ['notify', 'message', 'alert', 'show']):
            return 'communication'
        elif any(word in func_name for word in ['validate', 'check', 'verify', 'confirm']):
            return 'validation'
        elif any(word in func_name for word in ['process', 'handle', 'execute', 'run']):
            return 'processing'
        elif any(word in func_name for word in ['search', 'find', 'query', 'get', 'fetch']):
            return 'data_retrieval'
        elif any(word in func_name for word in ['save', 'update', 'create', 'add', 'insert']):
            return 'data_management'
        elif any(word in func_name for word in ['generate', 'build', 'make', 'produce']):
            return 'generation'
        else:
            return 'utility'
    
    def _get_function_business_purpose(self, category, func_name):
        """Get business purpose based on function category using LLM and Fine-Tuning-data"""
        return self._generate_dynamic_function_description(
            "business_purpose", category, func_name,
            "What is the specific business purpose of this function?"
        )
    
    def _get_function_operational_role(self, category):
        """Get operational role based on function category using LLM and Fine-Tuning-data"""
        return self._generate_dynamic_function_description(
            "operational_role", category, "",
            "What operational role does this function category serve in business operations?"
        )
    
    def _generate_dynamic_function_description(self, description_type, category, func_name, question):
        """Generate dynamic function descriptions using LLM and Fine-Tuning-data context"""
        
        # Create cache key to avoid redundant LLM calls
        cache_key = f"{description_type}_{category}_{func_name}"
        if cache_key in self._description_cache:
            cached_result = self._description_cache[cache_key]
            print(f"Using cached {description_type} for function {func_name}: {cached_result[:40]}...")
            return cached_result
        
        try:
            # Get business context from RAG system
            business_context_summary = ""
            if hasattr(self, 'rag_system') and self.rag_system:
                # Create a more specific query to get diverse business terms
                query = f"{category} {func_name} business function operations {description_type} workflow process"
                rag_context = self.rag_system.retrieve_relevant_context(query, top_k=5)
                
                if rag_context and rag_context.business_terms:
                    business_context_summary = "\n".join([
                        f"- {term['term']}: {term['definition']}" 
                        for term in rag_context.business_terms[:3]
                    ])
            
            # Create LLM prompt for dynamic function description generation
            prompt = f"""Based on the business context provided, analyze this function category and generate an appropriate description.

**BUSINESS CONTEXT:**
{business_context_summary if business_context_summary else "General business context"}

**FUNCTION INFORMATION:**
- Function Name: {func_name}
- Function Category: {category}
- Description Type: {description_type}

**QUESTION:**
{question}

**REQUIREMENTS:**
- Generate a specific, business-relevant description
- Focus on the actual business domain and terminology provided
- Be concise but informative (1-2 sentences maximum)
- Use business terminology from the context when relevant
- Complete the description properly without leaving hanging text

**OUTPUT:**
Provide only the description text, no additional formatting or explanation."""

            # Call LLM to generate dynamic description
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst who specializes in function analysis within business applications. Generate specific, business-relevant descriptions for application functions based on their categories and business context."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            # Extract and clean the response
            description = response.choices[0].message.content.strip()
            
            # Remove quotes and extra formatting
            description = description.strip('"\'').strip()
            
            # Cache the result for future use
            self._description_cache[cache_key] = description
            
            print(f"Generated dynamic {description_type} for function {func_name}: {description[:40]}...")
            return description
            
        except Exception as e:
            print(f"Error generating {description_type} for function {func_name}: {str(e)}")
            # Return intelligent fallback and cache it
            fallback_result = self._get_fallback_function_description(description_type, category, func_name)
            self._description_cache[cache_key] = fallback_result
            return fallback_result
    
    def _get_fallback_function_description(self, description_type, category, func_name):
        """Get fallback function description when LLM fails"""
        fallbacks = {
            'business_purpose': {
                'communication': 'Facilitates user communication and system feedback within business operations',
                'validation': 'Ensures data quality and business rule compliance',
                'processing': 'Executes core business logic and operational processes',
                'data_retrieval': 'Provides access to business information and operational data',
                'data_management': 'Maintains business data integrity and operational records',
                'generation': 'Creates business artifacts and operational resources',
                'utility': f'Supports business operations through {func_name or "utility"} functionality'
            },
            'operational_role': {
                'communication': 'User experience enhancement and system transparency',
                'validation': 'Quality assurance and operational risk management',
                'processing': 'Business process automation and workflow execution',
                'data_retrieval': 'Decision support and operational information access',
                'data_management': 'Data integrity maintenance and operational persistence',
                'generation': 'Resource creation and operational automation',
                'utility': 'System support and operational efficiency enhancement'
            }
        }
        
        category_fallbacks = fallbacks.get(description_type, {})
        return category_fallbacks.get(category, 
            f'Supports business operations through {category} {description_type.replace("_", " ")}')
    
    def _determine_state_business_context(self, state_var, rag_context):
        """Determine business context for global state variables - generic approach"""
        var_name = getattr(state_var, 'name', '').lower()
        var_type = getattr(state_var, 'type', '').lower()
        
        # Classify state variable generically
        state_category = self._classify_state_category(var_name, var_type)
        
        business_context = {
            'state_category': state_category,
            'business_purpose': self._generate_dynamic_state_description(
                "business_purpose", state_category, var_name, rag_context,
                "What is the business purpose of this state variable?"
            ),
            'operational_role': self._generate_dynamic_state_description(
                "operational_role", state_category, var_name, rag_context,
                "What operational role does this state variable serve?"
            )
        }
        
        # Add business term context if applicable
        matching_terms = self._find_matching_business_terms(var_name, rag_context.business_terms)
        if matching_terms:
            business_context['related_business_concepts'] = matching_terms
        
        return business_context
    
    def _classify_state_category(self, var_name, var_type):
        """Classify state variable into generic categories"""
        if any(word in var_name for word in ['current', 'active', 'selected']):
            return 'context_management'
        elif any(word in var_name for word in ['data', 'items', 'list', 'records']):
            return 'data_state'
        elif any(word in var_name for word in ['loading', 'pending', 'processing']):
            return 'process_state'
        elif any(word in var_name for word in ['error', 'message', 'notification']):
            return 'communication_state'
        elif any(word in var_name for word in ['show', 'display', 'visible', 'open']):
            return 'ui_state'
        elif any(word in var_name for word in ['config', 'setting', 'option']):
            return 'configuration_state'
        else:
            return 'business_state'
    
    def _generate_dynamic_state_description(self, description_type, category, var_name, rag_context, question):
        """Generate dynamic state descriptions using LLM and Fine-Tuning-data context"""
        try:
            # Get business context from RAG system
            business_context_summary = ""
            if rag_context and rag_context.business_terms:
                business_context_summary = "\n".join([
                    f"- {term['term']}: {term['definition']}" 
                    for term in rag_context.business_terms[:3]
                ])
            
            # Create LLM prompt for dynamic state description generation
            prompt = f"""Based on the business context provided, analyze this state variable and generate an appropriate description.

**BUSINESS CONTEXT:**
{business_context_summary if business_context_summary else "General business context"}

**STATE VARIABLE INFORMATION:**
- Variable Name: {var_name}
- Variable Category: {category}
- Description Type: {description_type}

**QUESTION:**
{question}

**REQUIREMENTS:**
- Generate a specific, business-relevant description
- Focus on the actual business domain and terminology provided
- Be concise but informative (1-2 sentences maximum)
- Use business terminology from the context when relevant
- Complete the description properly without leaving hanging text

**OUTPUT:**
Provide only the description text, no additional formatting or explanation."""

            # Call LLM to generate dynamic description
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst who specializes in state management within business applications. Generate specific, business-relevant descriptions for application state variables."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            # Extract and clean the response
            description = response.choices[0].message.content.strip()
            
            # Remove quotes and extra formatting
            description = description.strip('"\'').strip()
            
            print(f"Generated dynamic {description_type} for state {var_name}: {description[:40]}...")
            return description
            
        except Exception as e:
            print(f"Error generating {description_type} for state {var_name}: {str(e)}")
            # Return intelligent fallback
            return self._get_fallback_state_description(description_type, category, var_name)
    
    def _get_fallback_state_description(self, description_type, category, var_name):
        """Get fallback state description when LLM fails"""
        fallbacks = {
            'business_purpose': {
                'context_management': 'Manages user context and workflow focus within business operations',
                'data_state': 'Maintains critical business data and operational information',
                'process_state': 'Tracks business process execution status and workflow state',
                'communication_state': 'Manages user communication and system feedback',
                'ui_state': 'Controls user interface state for business interactions',
                'configuration_state': 'Maintains system and business configuration settings',
                'business_state': f'Manages business-specific state for {var_name or "application operations"}'
            },
            'operational_role': {
                'context_management': 'Enhances user productivity and workflow efficiency',
                'data_state': 'Ensures business data integrity and availability',
                'process_state': 'Provides process transparency and operational control',
                'communication_state': 'Improves user experience and error prevention',
                'ui_state': 'Maintains interface responsiveness and usability',
                'configuration_state': 'Enables system flexibility and customization',
                'business_state': 'Supports business process execution and state management'
            }
        }
        
        category_fallbacks = fallbacks.get(description_type, {})
        return category_fallbacks.get(category, 
            f'Supports business operations through {category} {description_type.replace("_", " ")}')
    
    def _create_business_templates(self, rag_context):
        """Create standardized business context templates to avoid duplication"""
        templates = {
            'workflow_template': {
                'process_name': 'Generic Business Process',
                'description': 'Standard business workflow processing',
                'stages': ['initiation', 'processing', 'validation', 'completion'],
                'business_value': 'Supports operational efficiency and compliance'
            },
            'data_template': {
                'data_type': 'Business Data',
                'purpose': 'Supports business operations and decision making',
                'lifecycle': ['creation', 'processing', 'validation', 'storage'],
                'business_impact': 'Critical for operational continuity'
            },
            'interface_template': {
                'ui_purpose': 'Business Process Interface',
                'user_value': 'Enables efficient business task completion',
                'interaction_patterns': ['display', 'input', 'validation', 'submission'],
                'business_benefit': 'Improves user productivity and accuracy'
            }
        }
        
        # Enhance templates with specific business terms from RAG context
        if rag_context and rag_context.business_terms:
            # Group business terms by category for template enhancement
            term_categories = {}
            for term in rag_context.business_terms[:10]:  # Limit to top 10 most relevant
                category = self._categorize_business_term(term['term'])
                if category not in term_categories:
                    term_categories[category] = []
                term_categories[category].append(term)
            
            # Enhance templates with categorized terms
            templates['business_terminology'] = term_categories
        
        return templates
    
    def _categorize_business_term(self, term):
        """Categorize business terms into logical groups"""
        term_lower = term.lower()
        
        if any(word in term_lower for word in ['process', 'workflow', 'procedure', 'operation']):
            return 'processes'
        elif any(word in term_lower for word in ['data', 'information', 'record', 'entry']):
            return 'data_concepts'
        elif any(word in term_lower for word in ['system', 'application', 'tool', 'interface']):
            return 'systems'
        elif any(word in term_lower for word in ['user', 'role', 'person', 'team']):
            return 'roles'
        else:
            return 'general_business'
    
    def _get_standardized_screen_business_context(self, screen, screen_specific_terms, screen_workflows, business_templates):
        """Generate standardized business context for screens - generic approach"""
        screen_name = str(getattr(screen, 'name', '') or '').lower()
        screen_desc = str(getattr(screen, 'description', '') or '').lower()
        
        # Classify screen type generically
        screen_category = self._classify_screen_category(screen_name, screen_desc)
        
        business_context = {
            'screen_category': screen_category,
            'business_purpose': self._get_screen_business_purpose(screen_category, screen_name),
            'workflow_role': self._get_screen_workflow_role(screen_category),
            'user_value_proposition': self._get_screen_user_value(screen_category),
            'operational_impact': self._get_screen_operational_impact(screen_category)
        }
        
        # Add relevant business terms if any
        if screen_specific_terms:
            business_context['related_business_concepts'] = screen_specific_terms[:3]  # Limit to top 3
        
        # Add workflow information if any
        if screen_workflows:
            business_context['process_workflows'] = screen_workflows[:2]  # Limit to top 2
        
        # Add template-based enhancements
        if business_templates and screen_category in ['data_entry', 'data_display', 'process_management']:
            template_key = self._map_screen_to_template(screen_category)
            if template_key in business_templates:
                business_context['template_guidance'] = business_templates[template_key]
        
        return business_context
    
    def _classify_screen_category(self, screen_name, screen_desc):
        """Classify screen into generic business categories"""
        combined_text = f"{screen_name} {screen_desc}".lower()
        
        if any(word in combined_text for word in ['dashboard', 'overview', 'summary', 'main']):
            return 'dashboard'
        elif any(word in combined_text for word in ['entry', 'input', 'create', 'add', 'new']):
            return 'data_entry'
        elif any(word in combined_text for word in ['maintenance', 'edit', 'update', 'modify']):
            return 'data_maintenance'
        elif any(word in combined_text for word in ['inquiry', 'search', 'lookup', 'find']):
            return 'data_inquiry'
        elif any(word in combined_text for word in ['list', 'worklist', 'queue', 'items']):
            return 'data_display'
        elif any(word in combined_text for word in ['process', 'workflow', 'approval', 'review']):
            return 'process_management'
        elif any(word in combined_text for word in ['report', 'analysis', 'tracking']):
            return 'reporting'
        else:
            return 'business_function'
    
    def _get_screen_business_purpose(self, category, screen_name):
        """Get business purpose based on screen category"""
        purposes = {
            'dashboard': 'Provides centralized visibility and control over key business metrics and operations',
            'data_entry': 'Enables efficient capture and input of business-critical information',
            'data_maintenance': 'Supports ongoing data quality and business information accuracy',
            'data_inquiry': 'Facilitates quick access to business information for decision-making',
            'data_display': 'Organizes and presents business data for operational efficiency',
            'process_management': 'Manages and controls key business processes and workflows',
            'reporting': 'Provides business intelligence and operational insights',
            'business_function': f'Supports specific business operations related to {screen_name}'
        }
        return purposes.get(category, 'Enables business operations and user productivity')
    
    def _get_screen_workflow_role(self, category):
        """Get workflow role based on screen category"""
        roles = {
            'dashboard': 'Central command and monitoring hub for business operations',
            'data_entry': 'Initial data capture point in business processes',
            'data_maintenance': 'Data quality assurance and correction in ongoing operations',
            'data_inquiry': 'Information access point for business decision support',
            'data_display': 'Information presentation for operational awareness',
            'process_management': 'Process control and workflow management interface',
            'reporting': 'Business intelligence and performance monitoring interface',
            'business_function': 'Specialized function within broader business processes'
        }
        return roles.get(category, 'Supports business process execution and management')
    
    def _get_screen_user_value(self, category):
        """Get user value proposition based on screen category"""
        values = {
            'dashboard': 'Quick situational awareness and rapid access to critical information',
            'data_entry': 'Streamlined data input with validation and guidance',
            'data_maintenance': 'Efficient correction and updating capabilities',
            'data_inquiry': 'Fast, accurate information retrieval for decision-making',
            'data_display': 'Clear, organized presentation of relevant business information',
            'process_management': 'Control and visibility over business process execution',
            'reporting': 'Actionable insights and performance visibility',
            'business_function': 'Specialized tools for specific business tasks'
        }
        return values.get(category, 'Enhanced productivity and operational efficiency')
    
    def _get_screen_operational_impact(self, category):
        """Get operational impact based on screen category"""
        impacts = {
            'dashboard': 'Improves decision-making speed and operational oversight',
            'data_entry': 'Ensures data quality and reduces processing time',
            'data_maintenance': 'Maintains data integrity and operational accuracy',
            'data_inquiry': 'Reduces information search time and improves accuracy',
            'data_display': 'Enhances operational visibility and coordination',
            'process_management': 'Streamlines workflows and ensures process compliance',
            'reporting': 'Enables data-driven decisions and performance optimization',
            'business_function': 'Supports specialized operational requirements'
        }
        return impacts.get(category, 'Contributes to overall operational efficiency and effectiveness')
    
    def _map_screen_to_template(self, category):
        """Map screen category to business template"""
        mapping = {
            'data_entry': 'interface_template',
            'data_display': 'data_template',
            'process_management': 'workflow_template'
        }
        return mapping.get(category, 'interface_template')
    
    def _get_standardized_element_business_context(self, element, screen_business_context, business_templates):
        """Generate standardized business context for UI elements - generic approach"""
        element_type = str(getattr(element, 'element_type', '') or '').lower()
        element_label = str(getattr(element, 'label', '') or '').lower()
        element_content = str(getattr(element, 'text_content', '') or '').lower()
        
        # Classify element purpose generically
        element_category = self._classify_element_category(element_type, element_label, element_content)
        
        business_context = {
            'element_category': element_category,
            'business_function': self._get_element_business_function(element_category, element_type),
            'user_interaction_purpose': self._get_element_user_purpose(element_category),
            'operational_value': self._get_element_operational_value(element_category),
            'workflow_contribution': self._get_element_workflow_contribution(element_category)
        }
        
        # Inherit screen-level context where relevant
        if screen_business_context and 'screen_category' in screen_business_context:
            screen_category = screen_business_context['screen_category']
            business_context['screen_context_alignment'] = self._align_element_with_screen(element_category, screen_category)
        
        return business_context
    
    def _classify_element_category(self, element_type, element_label, element_content):
        """Classify UI element into generic business categories"""
        combined_text = f"{element_type} {element_label} {element_content}".lower()
        
        if element_type in ['input', 'textarea']:
            if any(word in combined_text for word in ['search', 'find', 'lookup']):
                return 'data_search'
            elif any(word in combined_text for word in ['id', 'number', 'code']):
                return 'identifier_input'
            else:
                return 'data_input'
        elif element_type in ['button']:
            if any(word in combined_text for word in ['save', 'submit', 'create', 'add']):
                return 'action_commit'
            elif any(word in combined_text for word in ['search', 'find', 'lookup']):
                return 'action_search'
            elif any(word in combined_text for word in ['cancel', 'clear', 'reset']):
                return 'action_cancel'
            else:
                return 'action_trigger'
        elif element_type in ['select', 'dropdown']:
            return 'data_selection'
        elif element_type in ['table', 'grid']:
            return 'data_presentation'
        elif element_type in ['checkbox', 'radio']:
            return 'data_option'
        elif element_type in ['label', 'text']:
            return 'information_display'
        else:
            return 'interface_component'
    
    def _get_element_business_function(self, category, element_type):
        """Get business function based on element category using LLM and Fine-Tuning-data"""
        return self._generate_dynamic_element_description(
            "business_function", category, element_type,
            "What is the specific business function of this UI element?"
        )
    
    def _get_element_user_purpose(self, category):
        """Get user purpose based on element category using LLM and Fine-Tuning-data"""
        return self._generate_dynamic_element_description(
            "user_purpose", category, "",
            "What is the user experience purpose of this UI element category?"
        )
    
    def _get_element_operational_value(self, category):
        """Get operational value based on element category using LLM and Fine-Tuning-data"""
        return self._generate_dynamic_element_description(
            "operational_value", category, "",
            "What is the operational business value of this UI element category?"
        )
    
    def _get_element_workflow_contribution(self, category):
        """Get workflow contribution based on element category using LLM and Fine-Tuning-data"""
        return self._generate_dynamic_element_description(
            "workflow_contribution", category, "",
            "How does this UI element category contribute to business workflows?"
        )
    
    def _generate_dynamic_element_description(self, description_type, category, element_type, question):
        """Generate dynamic element descriptions using LLM and Fine-Tuning-data context"""
        try:
            # Get business context from RAG system
            business_context_summary = ""
            if hasattr(self, 'rag_system') and self.rag_system:
                # Create a query for element-related business terms
                query = f"{category} {element_type} business element UI"
                rag_context = self.rag_system.retrieve_relevant_context(query, top_k=3)
                
                if rag_context and rag_context.business_terms:
                    business_context_summary = "\n".join([
                        f"- {term['term']}: {term['definition']}" 
                        for term in rag_context.business_terms[:3]
                    ])
            
            # Create LLM prompt for dynamic description generation
            prompt = f"""Based on the business context and terminology provided, analyze this UI element category and generate an appropriate description.

**BUSINESS CONTEXT:**
{business_context_summary if business_context_summary else "General business context"}

**ELEMENT INFORMATION:**
- Element Category: {category}
- Element Type: {element_type}
- Description Type: {description_type}

**QUESTION:**
{question}

**REQUIREMENTS:**
- Generate a specific, business-relevant description
- Focus on the actual business domain and terminology provided
- Be concise but informative (1-2 sentences maximum)
- Avoid generic technical descriptions
- Use business terminology from the context when relevant

**OUTPUT:**
Provide only the description text, no additional formatting or explanation."""

            # Call LLM to generate dynamic description
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst who specializes in UI element analysis within business contexts. Generate specific, business-relevant descriptions based on the provided context and terminology."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            # Extract and clean the response
            description = response.choices[0].message.content.strip()
            
            # Remove quotes and extra formatting
            description = description.strip('"\'').strip()
            
            print(f"Generated dynamic {description_type} for {category}: {description[:50]}...")
            return description
            
        except Exception as e:
            print(f"Error generating dynamic {description_type} for {category}: {str(e)}")
            # Return intelligent fallback
            return self._get_fallback_element_description(description_type, category, element_type)
    
    def _get_fallback_element_description(self, description_type, category, element_type):
        """Get fallback description when LLM fails"""
        fallbacks = {
            'business_function': {
                'data_input': 'Captures business information for operational processing',
                'action_trigger': 'Initiates business operations and workflow processes',
                'data_selection': 'Enables business choice selection from defined options',
                'default': f'Supports business operations through {category} functionality'
            },
            'user_purpose': {
                'data_input': 'Efficient business data entry and validation',
                'action_trigger': 'Intuitive business process initiation',
                'data_selection': 'Guided business option selection',
                'default': f'Enhanced business productivity through {category} interaction'
            },
            'operational_value': {
                'data_input': 'Ensures business data quality and operational accuracy',
                'action_trigger': 'Streamlines business process execution',
                'data_selection': 'Standardizes business choices and reduces errors',
                'default': f'Contributes to operational efficiency through {category} management'
            },
            'workflow_contribution': {
                'data_input': 'Critical business data capture point for downstream processes',
                'action_trigger': 'Business process initiation and workflow orchestration',
                'data_selection': 'Business process configuration and routing control',
                'default': f'Supports business workflow execution through {category} interface'
            }
        }
        
        category_fallbacks = fallbacks.get(description_type, {})
        return category_fallbacks.get(category, category_fallbacks.get('default', 
            f'Supports business operations through {category} {element_type} interface'))
    
    def _align_element_with_screen(self, element_category, screen_category):
        """Describe how element aligns with screen's business purpose using LLM and Fine-Tuning-data"""
        return self._generate_dynamic_alignment_description(element_category, screen_category)
    
    def _generate_dynamic_alignment_description(self, element_category, screen_category):
        """Generate dynamic alignment description using LLM and Fine-Tuning-data context"""
        try:
            # Get business context from RAG system
            business_context_summary = ""
            if hasattr(self, 'rag_system') and self.rag_system:
                # Create a query for alignment-related business terms
                query = f"{element_category} {screen_category} business alignment workflow"
                rag_context = self.rag_system.retrieve_relevant_context(query, top_k=3)
                
                if rag_context and rag_context.business_terms:
                    business_context_summary = "\n".join([
                        f"- {term['term']}: {term['definition']}" 
                        for term in rag_context.business_terms[:3]
                    ])
            
            # Create LLM prompt for dynamic alignment description
            prompt = f"""Based on the business context provided, describe how a UI element aligns with its screen's business purpose.

**BUSINESS CONTEXT:**
{business_context_summary if business_context_summary else "General business context"}

**ALIGNMENT ANALYSIS:**
- Element Category: {element_category}
- Screen Category: {screen_category}

**QUESTION:**
How does this element category support and align with the screen's business purpose?

**REQUIREMENTS:**
- Describe the functional relationship between element and screen
- Focus on business value and operational alignment
- Be concise but specific (1 sentence)
- Use business terminology from the context when relevant
- Emphasize how the element serves the screen's business goals

**OUTPUT:**
Provide only the alignment description, no additional formatting or explanation."""

            # Call LLM to generate dynamic alignment description
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst who specializes in UI/UX alignment within business workflows. Generate specific descriptions of how UI elements support screen business purposes."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            # Extract and clean the response
            alignment_description = response.choices[0].message.content.strip()
            
            # Remove quotes and extra formatting
            alignment_description = alignment_description.strip('"\'').strip()
            
            print(f"Generated dynamic alignment for {element_category}+{screen_category}: {alignment_description[:40]}...")
            return alignment_description
            
        except Exception as e:
            print(f"Error generating alignment for {element_category}+{screen_category}: {str(e)}")
            # Return intelligent fallback
            return f'Supporting function - enhances {screen_category} capabilities through {element_category} interaction'
    
    def _create_rich_element_business_context(self, element, rag_context, screen_specific_terms):
        """Create rich business context like the setup guide example using RAG data"""
        element_type = getattr(element, 'element_type', '')
        element_text = getattr(element, 'text_content', '') or ''
        element_label = getattr(element, 'label', '') or ''
        
        # Extract relevant terms from element content
        element_content = f"{element_type} {element_text} {element_label}".lower()
        
        # Find matching business terms
        matching_terms = []
        related_processes = []
        business_context_description = ""
        
        # Check against RAG business terms with improved matching
        for term_info in rag_context.business_terms:
            term = term_info['term']
            definition = term_info['definition']
            
            # Improved relevance checking - must have direct relevance
            is_relevant = False
            
            # Exact match in element content
            if term.lower() in element_content:
                is_relevant = True
            # Check if element label/text matches term
            elif element_label and term.lower() in element_label.lower():
                is_relevant = True
            # Check if any words from the term appear in element
            elif any(word.lower() in element_content for word in term.split() if len(word) > 2):
                is_relevant = True
            # Screen-specific terms
            elif any(term.lower() in screen_term.lower() for screen_term in screen_specific_terms):
                is_relevant = True
            
            if is_relevant:
                matching_terms.append({
                    'term': term,
                    'definition': definition
                })
                
                # Extract workflow processes related to this term
                if 'workflow' in definition.lower() or 'process' in definition.lower():
                    related_processes.append(f"{term} workflow")
        
        # Create specific business context based on element type and found terms
        if element_type == 'button':
            # Check for specific patterns first
            if 'RTV' in element_content.upper() or 'RTV' in str(screen_specific_terms).upper():
                business_context_description = "Button to process Return to Vendor workflow - returns merchandise back to supplier"
                related_processes.extend(["RTV workflow", "vendor returns", "disposition processing"])
            elif 'approve' in element_content.lower():
                business_context_description = "Authorization button for workflow approval - allows items to proceed to next stage"
                related_processes.extend(["approval workflow", "authorization process", "workflow progression"])
            elif 'NSI' in element_content.upper() or 'NSI' in str(screen_specific_terms).upper():
                business_context_description = "Button for NSI (Non Salable Inventory) management operations"
                related_processes.extend(["NSI processing", "inventory management", "item disposition"])
            elif matching_terms:
                primary_term = matching_terms[0]
                # Format based on the business term found
                if 'process' in primary_term['definition'].lower():
                    business_context_description = f"Button to {primary_term['definition'].lower()}"
                else:
                    business_context_description = f"Button for {primary_term['term']} operations - {primary_term['definition']}"
            else:
                business_context_description = "Interactive button for business process execution"
        
        elif element_type == 'input':
            if matching_terms:
                primary_term = matching_terms[0]
                business_context_description = f"Input field for {primary_term['term']} - {primary_term['definition']}"
            else:
                business_context_description = "Data input field for business information capture"
        
        elif element_type == 'select':
            if matching_terms:
                primary_term = matching_terms[0]
                business_context_description = f"Selection control for {primary_term['term']} options - {primary_term['definition']}"
            else:
                business_context_description = "Selection control for business configuration options"
        
        # Build rich business context object
        rich_context = {
            "type": element_type,
            "label": element_label or f"{element_type.title()} Element",
            "description": business_context_description
        }
        
        # Add business context if we found relevant terms
        if matching_terms:
            primary_term = matching_terms[0]['term']
            if 'NSI' in primary_term or 'RTV' in primary_term:
                rich_context["business_context"] = f"Part of {primary_term} (Non Salable Inventory) management workflow"
            else:
                rich_context["business_context"] = f"Part of {primary_term} business operations"
        
        # Add related processes if found
        if related_processes:
            rich_context["related_processes"] = related_processes[:3]  # Limit to top 3
        
        return rich_context
    
    def _set_attribute_safe(self, obj, attr_name, value):
        """Safely set attribute on object, handling both dict and object types"""
        try:
            if hasattr(obj, '__dict__'):
                # It's an object with attributes
                setattr(obj, attr_name, value)
            elif isinstance(obj, dict):
                # It's a dictionary
                obj[attr_name] = value
            else:
                # Try to set as attribute anyway
                setattr(obj, attr_name, value)
        except Exception as e:
            print(f"Could not set {attr_name} on object: {str(e)}")
            # Continue processing without failing


def create_rag_enhanced_analyzer(openai_client, deployment_name: str, fine_tuning_data_folder: str = None) -> RAGEnhancedUIAnalyzer:
    """Factory function to create RAG-enhanced analyzer"""
    
    if fine_tuning_data_folder is None:
        # Use default path relative to current script
        fine_tuning_data_folder = os.path.join(os.path.dirname(__file__), "Fine-Tuning-data")
    
    return RAGEnhancedUIAnalyzer(openai_client, deployment_name, fine_tuning_data_folder)


# Example usage and testing
if __name__ == "__main__":
    # Test the RAG system
    fine_tuning_folder = "Fine-Tuning-data"
    
    if os.path.exists(fine_tuning_folder):
        rag_system = BusinessTerminologyRAG(fine_tuning_folder)
        
        # Test queries
        test_queries = [
            "RTV process and returns",
            "inventory management workflow", 
            "NSI entry and processing",
            "shipment tracking and BOL"
        ]
        
        print("\nTesting RAG Context Retrieval:")
        print("=" * 50)
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            context = rag_system.retrieve_relevant_context(query, top_k=3)
            print(f"Relevance Score: {context.relevance_score:.3f}")
            print(f"Business Terms Found: {len(context.business_terms)}")
            print(f"Similar Examples: {len(context.similar_examples)}")
            
            if context.business_terms:
                print("Top Business Term:", context.business_terms[0]['term'])
            
            print("-" * 30)
    else:
        print("Fine-Tuning-data folder not found")
