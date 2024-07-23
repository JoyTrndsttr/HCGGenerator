# Generators/GoGenerator.py
from tree_sitter import Language, Parser
import logging

# 设置日志记录
logging.basicConfig(filename='debug.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')

def load_language(language_path):
    parser = Parser()
    parser.language = Language(language_path)
    return parser

def extract_imports(node):
    imports = {}
    for child in node.children:
        if child.type == 'import_declaration':
            for grandchild in child.children:
                if grandchild.type == 'import_spec_list':
                    for spec in grandchild.children:
                        if spec.type == 'import_spec':
                            path_node = spec.child_by_field_name('path')
                            if path_node:
                                import_path = path_node.text.decode('utf-8').strip('"')
                                imports[import_path.split('/')[-1]] = import_path
                elif grandchild.type == 'import_spec':
                    path_node = grandchild.child_by_field_name('path')
                    if path_node:
                        import_path = path_node.text.decode('utf-8').strip('"')
                        imports[import_path.split('/')[-1]] = import_path
    if imports:
        logging.debug(f"Imports extracted: {imports}")
    return imports

def extract_functions_and_calls(node, module_name, imports, functions=None, calls=None, current_function=None):
    if functions is None:
        functions = {}
    if calls is None:
        calls = {}

    def process_function_definition(child):
        name_node = child.child_by_field_name('name')
        parameters = child.child_by_field_name('parameters')
        if name_node:
            function_name = name_node.text.decode('utf-8')
            param_list = []
            if parameters:
                for param in parameters.children:
                    if param.type == 'parameter_declaration':
                        param_list.append(param.text.decode('utf-8'))
            param_str = ', '.join(param_list)
            current_function = f"{module_name}.{function_name}({param_str})"
            functions[current_function] = []
        return current_function

    def process_call_expression(call_node):
        call_name_node = call_node.child_by_field_name('function')
        argument_list = call_node.child_by_field_name('arguments')
        if call_name_node:
            call_name_parts = call_name_node.text.decode('utf-8').split('.')
            call_args = []
            if argument_list:
                for arg in argument_list.children:
                    if arg.type == 'identifier':
                        call_args.append(arg.text.decode('utf-8'))
            call_args_str = ', '.join(call_args)
            if len(call_name_parts) > 1 and call_name_parts[0] in imports:
                call_name = f"{imports[call_name_parts[0]]}.{call_name_parts[1]}({call_args_str})"
            else:
                call_name = f"{module_name}.{call_name_node.text.decode('utf-8')}({call_args_str})"
            if current_function:
                functions[current_function].append(call_name)
            if call_name not in calls:
                calls[call_name] = []
            calls[call_name].append(current_function)

    for child in node.children:
        if child.type == 'function_declaration':
            current_function = process_function_definition(child)
            extract_functions_and_calls(child, module_name, imports, functions, calls, current_function)
        elif child.type == 'call_expression':
            process_call_expression(child)
        else:
            extract_functions_and_calls(child, module_name, imports, functions, calls, current_function)

    return functions, calls
