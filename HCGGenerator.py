#HCGGenerator.py
import os
import logging
from tree_sitter import Language, Parser
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
import tree_sitter_c_sharp as tscs
import tree_sitter_go as tsgo
import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjs
import tree_sitter_python as tspython
import tree_sitter_ruby as tsruby
from Generators import PythonGenerator, GoGenerator, JavaGenerator, CGenerator, CppGenerator, CSharpGenerator, JavaScriptGenerator, RubyGenerator

# 设置日志记录
logging.basicConfig(filename='debug.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')

# 初始化语言库路径
def init_languages():
    languages = {}
    languages['c'] = Language(tsc.language())
    languages['cpp'] = Language(tscpp.language())
    languages['c-sharp'] = Language(tscs.language())
    languages['go'] = Language(tsgo.language())
    languages['java'] = Language(tsjava.language())
    languages['javascript'] = Language(tsjs.language())
    languages['python'] = Language(tspython.language())
    languages['ruby'] = Language(tsruby.language())
    return languages

# 加载语言包
def load_language(language):
    parser = Parser()
    parser.language = language
    return parser

# 解析代码文件
def parse_file(file_path, parser):
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read().encode('utf8')
    tree = parser.parse(source_code)
    return tree

# 构建文件层次树并生成调用图
def build_file_hierarchy_and_call_graph(root_dir, language_parsers):
    hierarchy = {}
    functions = {}
    calls = {}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        parts = os.path.relpath(dirpath, root_dir).split(os.sep)
        subdir = hierarchy
        for part in parts:
            subdir = subdir.setdefault(part, {})
        for filename in filenames:
            file_extension = os.path.splitext(filename)[1]
            if file_extension in language_parsers:
                subdir[filename] = {}
                file_path = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(file_path, root_dir)
                module_name = os.path.splitext(relative_path.replace(os.sep, '.'))[0]
                parser = language_parsers[file_extension]
                tree = parse_file(file_path, parser)
                
                if file_extension == '.py':
                    imports = PythonGenerator.extract_imports(tree.root_node)
                    file_functions, file_calls = PythonGenerator.extract_functions_and_calls(tree.root_node, module_name, imports)
                elif file_extension == '.go':
                    imports = GoGenerator.extract_imports(tree.root_node)
                    file_functions, file_calls = GoGenerator.extract_functions_and_calls(tree.root_node, module_name, imports)
                # elif file_extension == '.java':
                #     imports = JavaGenerator.extract_imports(tree.root_node)
                #     file_functions, file_calls = JavaGenerator.extract_functions_and_calls(tree.root_node, module_name, imports)
                # elif file_extension == '.c':
                #     imports = CGenerator.extract_imports(tree.root_node)
                #     file_functions, file_calls = CGenerator.extract_functions_and_calls(tree.root_node, module_name, imports)
                elif file_extension == '.cpp':
                    imports = CppGenerator.extract_imports(tree.root_node)
                    file_functions, file_calls = CppGenerator.extract_functions_and_calls(tree.root_node, module_name, imports)
                # elif file_extension == '.cs':
                #     imports = CSharpGenerator.extract_imports(tree.root_node)
                #     file_functions, file_calls = CSharpGenerator.extract_functions_and_calls(tree.root_node, module_name, imports)
                # elif file_extension == '.js':
                #     imports = JavaScriptGenerator.extract_imports(tree.root_node)
                #     file_functions, file_calls = JavaScriptGenerator.extract_functions_and_calls(tree.root_node, module_name, imports)
                # elif file_extension == '.rb':
                #     imports = RubyGenerator.extract_imports(tree.root_node)
                #     file_functions, file_calls = RubyGenerator.extract_functions_and_calls(tree.root_node, module_name, imports)
                else:
                    continue

                functions.update(file_functions)
                for call, funcs in file_calls.items():
                    if call in calls:
                        calls[call].extend(funcs)
                    else:
                        calls[call] = funcs

    return hierarchy, functions, calls

# 输出层次调用图到文件
def output_hierarchy_call_graph(repo_path, file_hierarchy, functions, calls, output_file, language_parsers):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    def write_hierarchy_and_calls(subdir, indent=0):
        for name, content in subdir.items():
            f.write('  ' * indent + name + '\n')
            if name.endswith(tuple(language_parsers.keys())):
                for function, called_functions in functions.items():
                    if function.startswith(name):
                        f.write('  ' * (indent + 1) + function.split('.')[-1] + '()\n')
                        for called_function in called_functions:
                            f.write('  ' * (indent + 2) + '-> ' + called_function + '\n')
            if isinstance(content, dict):
                write_hierarchy_and_calls(content, indent + 1)

    with open(output_file, 'w', encoding='utf-8') as f:
        write_hierarchy_and_calls(file_hierarchy, 0)

        f.write('\nCall Graph:\n')
        for function, called_functions in functions.items():
            for called_function in called_functions:
                f.write(f"{function} -> {called_function}\n")

# 主函数
def main():
    # 设置项目路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_base_path = os.path.join(script_dir, 'repo')
    output_base_path = os.path.join(script_dir, 'HCGraph')

    # 加载所有语言解析器
    languages = init_languages()

    # 创建语言解析器映射
    language_parsers = {
        '.c': load_language(languages['c']),
        '.cpp': load_language(languages['cpp']),
        '.cs': load_language(languages['c-sharp']),
        '.go': load_language(languages['go']),
        '.java': load_language(languages['java']),
        '.js': load_language(languages['javascript']),
        '.py': load_language(languages['python']),
        '.rb': load_language(languages['ruby']),
    }

    for repo_name in os.listdir(repo_base_path):
        repo_path = os.path.join(repo_base_path, repo_name)
        if os.path.isdir(repo_path):
            file_hierarchy, functions, calls = build_file_hierarchy_and_call_graph(repo_path, language_parsers)

            # 调试信息
            logging.debug(f"Processing repository: {repo_name}")
            logging.debug(f"File Hierarchy: {file_hierarchy}")
            logging.debug(f"Functions: {functions}")
            logging.debug(f"Calls: {calls}")

            output_file = os.path.join(output_base_path, f"{repo_name}_HCGraph.txt")
            output_hierarchy_call_graph(repo_path, file_hierarchy, functions, calls, output_file, language_parsers)

if __name__ == "__main__":
    main()
