import argparse
import sys
import os
from typing import Dict, Any, List, Set
import urllib.request
import urllib.error
import re
import gzip
import io

class DependencyVisualizer:
    def __init__(self):
        self.config = {}
        self.visited_packages = set()
        self.dependency_graph = {}
        self.reverse_dependency_graph = {}
        
    def load_config_from_csv(self, config_file: str) -> Dict[str, Any]:
        config = {}
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if ';' in line:
                            parts = line.split(';', 1)
                        elif ',' in line:
                            parts = line.split(',', 1)
                        else:
                            print(f"Предупреждение: строка {line_num} пропущена - неверный формат: {line}")
                            continue
                        
                        if len(parts) == 2:
                            key, value = parts
                            key = key.strip()
                            value = value.strip()
                            
                            if value.lower() in ['true', 'false']:
                                value = value.lower() == 'true'
                            elif value.isdigit():
                                value = int(value)
                                
                            config[key] = value
                        else:
                            print(f"Предупреждение: строка {line_num} пропущена - неверный формат: {line}")
                            
        except FileNotFoundError:
            raise ValueError(f"Конфигурационный файл не найден: {config_file}")
        except Exception as e:
            raise ValueError(f"Ошибка чтения конфигурационного файла: {str(e)}")
            
        return config
    
    def validate_config(self, config: Dict[str, Any]) -> None:
        required_params = [
            'package',
            'repository',
            'test_mode',
            'ascii_tree',
            'filter_substring'
        ]
        
        for param in required_params:
            if param not in config:
                raise ValueError(f"Отсутствует обязательный параметр: {param}")
        
        if config.get('test_mode') and not config.get('test_file'):
            raise ValueError("В тестовом режиме должен быть указан test_file")

        repo_url = config.get('repository', '')
        if not repo_url:
            raise ValueError("URL репозитория или путь к файлу не может быть пустым")
        
        test_mode = config.get('test_mode')
        if not isinstance(test_mode, bool):
            raise ValueError("Режим тестирования должен быть true или false")
        
        ascii_tree = config.get('ascii_tree')
        if not isinstance(ascii_tree, bool):
            raise ValueError("Режим ASCII-дерева должен быть true или false")
    
    def print_config(self, config: Dict[str, Any]) -> None:
        print("Текущая конфигурация:")
        print("-" * 40)
        for key, value in config.items():
            print(f"{key}: {value}")
        print("-" * 40)
    
    def get_package_dependencies_ubuntu(self, package_name: str, repo_url: str) -> List[str]:
        dependencies = []
    
        try:
            if "ubuntu.com" in repo_url:
                url = f"{repo_url}/dists/focal/main/binary-amd64/Packages.gz"
            else:
                url = f"{repo_url}/Packages"
            
            print(f"Загрузка информации о пакете из: {url}")
            
            with urllib.request.urlopen(url) as response:
                if url.endswith('.gz'):
                    compressed_file = io.BytesIO(response.read())
                    with gzip.GzipFile(fileobj=compressed_file) as f:
                        content = f.read().decode('utf-8', errors='ignore')
                else:
                    content = response.read().decode('utf-8', errors='ignore')
                
                package_pattern = f"Package: {package_name}"
                if package_pattern in content:
                    start_idx = content.find(package_pattern)
                    end_idx = content.find("\n\n", start_idx)
                    package_info = content[start_idx:end_idx]
                    
                    dep_pattern = r"Depends:\s*(.+)"
                    match = re.search(dep_pattern, package_info)
                    
                    if match:
                        depends_line = match.group(1)
                        deps = re.findall(r'([a-zA-Z0-9\-\.]+)', depends_line)
                        dependencies = [dep.strip() for dep in deps if dep.strip()]
                
        except urllib.error.URLError as e:
            raise ValueError(f"Ошибка при загрузке данных из репозитория: {str(e)}")
        except Exception as e:
            raise ValueError(f"Ошибка при обработке данных пакета: {str(e)}")
        
        return dependencies
    
    def get_test_dependencies(self, package_name: str, test_file: str) -> List[str]:
        dependencies = []
        
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                lines = content.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if '->' in line:
                        parts = line.split('->', 1)
                        if len(parts) == 2:
                            pkg, deps = parts
                            if pkg.strip() == package_name:
                                dependencies = [dep.strip() for dep in deps.split(',') if dep.strip()]
                                break
                            
        except FileNotFoundError:
            raise ValueError(f"Тестовый файл не найден: {test_file}")
        except Exception as e:
            raise ValueError(f"Ошибка чтения тестового файла: {str(e)}")
        
        return dependencies
    
    def collect_dependencies(self, config: Dict[str, Any]) -> List[str]:
        package_name = config['package']
        test_mode = config['test_mode']
        
        print(f"\nСбор данных для пакета: {package_name}")
        print(f"Режим тестирования: {'включен' if test_mode else 'выключен'}")
        
        dependencies = []
        
        if test_mode:
            print("Используется тестовый режим")
            test_file = config.get('test_file', 'test.txt')
            dependencies = self.get_test_dependencies(package_name, test_file)
        else:
            repository = config['repository']
            print(f"Подключение к репозиторию: {repository}")
            dependencies = self.get_package_dependencies_ubuntu(package_name, repository)
        
        return dependencies
    
    def print_dependencies(self, dependencies: List[str], package_name: str) -> None:
        print(f"\nПрямые зависимости пакета '{package_name}':")
        print("-" * 40)
        
        if not dependencies:
            print("Зависимости не найдены")
        else:
            for i, dep in enumerate(dependencies, 1):
                print(f"{i}. {dep}")
        
        print("-" * 40)
    
    def build_dependency_graph_dfs(self, package_name: str, config: Dict[str, Any], current_path: List[str] = None) -> Set[str]:
        if current_path is None:
            current_path = []
        
        if package_name in current_path:
            cycle_path = ' -> '.join(current_path + [package_name])
            print(f"Обнаружена циклическая зависимость: {cycle_path}")
            return set()
        
        filter_substring = config.get('filter_substring', '')
        if filter_substring and filter_substring in package_name:
            print(f"Пакет '{package_name}' отфильтрован по подстроке '{filter_substring}'")
            return set()

        if package_name in self.dependency_graph:
            return self.dependency_graph[package_name]
        
        dependencies = []
        if config['test_mode']:
            test_file = config.get('test_file', 'test.txt')
            dependencies = self.get_test_dependencies(package_name, test_file)
        else:
            repository = config['repository']
            dependencies = self.get_package_dependencies_ubuntu(package_name, repository)
        
        self.dependency_graph[package_name] = set(dependencies)
        
        for dep in dependencies:
            if dep not in self.reverse_dependency_graph:
                self.reverse_dependency_graph[dep] = set()
            self.reverse_dependency_graph[dep].add(package_name)
        
        new_path = current_path + [package_name]
        all_dependencies = set(dependencies)
        
        for dep in dependencies:
            if dep not in self.visited_packages:
                self.visited_packages.add(dep)
                transitive_deps = self.build_dependency_graph_dfs(dep, config, new_path)
                all_dependencies.update(transitive_deps)
        
        self.dependency_graph[package_name] = all_dependencies
        
        return all_dependencies
    
    def print_dependency_graph(self, config: Dict[str, Any]) -> None:
        package_name = config['package']
        ascii_tree = config.get('ascii_tree', False)
        
        print(f"\nПолный граф зависимостей пакета '{package_name}':")
        print("-" * 50)
        
        if package_name not in self.dependency_graph:
            print("Граф зависимостей не построен")
            return
        
        if ascii_tree:
            self._print_ascii_tree(package_name, set())
        else:
            self._print_simple_list(package_name)
        
        print("-" * 50)
    
    def _print_simple_list(self, package_name: str, indent: int = 0, visited: Set[str] = None) -> None:
        if visited is None:
            visited = set()
            
        if package_name in visited:
            print("  " * indent + f"└── {package_name} (уже показан)")
            return
            
        visited.add(package_name)
        dependencies = self.dependency_graph.get(package_name, set())
        
        if indent == 0:
            print(f"{package_name}")
        
        for dep in sorted(dependencies):
            print("  " * (indent + 1) + f"└── {dep}")
            if dep in self.dependency_graph and self.dependency_graph[dep]:
                self._print_simple_list(dep, indent + 2, visited.copy())
    
    def _print_ascii_tree(self, package_name: str, visited: Set[str], prefix: str = "") -> None:
        if package_name in visited:
            print(f"{prefix}└── {package_name} (цикл)")
            return
        
        visited.add(package_name)
        dependencies = self.dependency_graph.get(package_name, set())
        
        print(f"{prefix}{package_name}")
        
        if dependencies:
            sorted_deps = sorted(dependencies)
            for i, dep in enumerate(sorted_deps):
                is_last = i == len(sorted_deps) - 1
                new_prefix = prefix + ("    " if is_last else "│   ")
                connector = "└── " if is_last else "├── "
                
                print(f"{prefix}{connector}", end="")
                self._print_ascii_tree(dep, visited.copy(), new_prefix)
    
    def find_reverse_dependencies(self, target_package: str, config: Dict[str, Any]) -> Set[str]:
        reverse_deps = set()
        
        if target_package in self.reverse_dependency_graph:
            return self.reverse_dependency_graph[target_package]
        
        if config['test_mode']:
            test_file = config.get('test_file', 'test.txt')
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    lines = content.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if '->' in line:
                            parts = line.split('->', 1)
                            if len(parts) == 2:
                                pkg, deps = parts
                                pkg = pkg.strip()
                                dependencies = [dep.strip() for dep in deps.split(',') if dep.strip()]
                                
                                if target_package in dependencies:
                                    reverse_deps.add(pkg)
                                    
            except Exception as e:
                print(f"Ошибка при поиске обратных зависимостей: {str(e)}")
        
        return reverse_deps
    
    def print_reverse_dependencies(self, target_package: str, config: Dict[str, Any]) -> None:
        print(f"\nОбратные зависимости пакета '{target_package}':")
        print("-" * 50)
        
        reverse_deps = self.find_reverse_dependencies(target_package, config)
        
        if not reverse_deps:
            print("Обратные зависимости не найдены")
        else:
            for i, dep in enumerate(sorted(reverse_deps), 1):
                print(f"{i}. {dep}")
        
        print("-" * 50)
    
    def run_stage1(self, config: Dict[str, Any]) -> None:
        print("Загрузка конфигурации...")
        self.validate_config(config)
        self.print_config(config)
        print("Конфигурация успешно загружена и валидирована!")
    
    def run_stage2(self, config: Dict[str, Any]) -> None:
        dependencies = self.collect_dependencies(config)
        self.print_dependencies(dependencies, config['package'])
        print("Данные о зависимостях успешно собраны!")
    
    def run_stage3(self, config: Dict[str, Any]) -> None:
        print("\nПостроение полного графа зависимостей...")
        
        self.visited_packages = set()
        self.dependency_graph = {}
        self.reverse_dependency_graph = {}
        
        package_name = config['package']
        filter_substring = config.get('filter_substring', '')
        
        print(f"Пакет: {package_name}")
        if filter_substring:
            print(f"Фильтрация по подстроке: '{filter_substring}'")
        
        all_dependencies = self.build_dependency_graph_dfs(package_name, config)
        
        self.print_dependency_graph(config)
        
        total_packages = len(self.dependency_graph)
        print(f"\nСтатистика графа:")
        print(f"Всего пакетов в графе: {total_packages}")
        if package_name in self.dependency_graph:
            direct_deps = len(self.collect_dependencies(config))
            transitive_deps = len(self.dependency_graph[package_name])
            print(f"Прямые зависимости: {direct_deps}")
            print(f"Транзитивные зависимости: {transitive_deps}")
        
        print("Граф зависимостей успешно построен!")
    
    def run_stage4(self, config: Dict[str, Any]) -> None:
        print("\nЭтап 4: Поиск обратных зависимостей")
        
        if not self.dependency_graph:
            print("Построение графа зависимостей...")
            self.visited_packages = set()
            self.dependency_graph = {}
            self.reverse_dependency_graph = {}
            self.build_dependency_graph_dfs(config['package'], config)
        
        target_package = input("Введите имя пакета для поиска обратных зависимостей: ").strip()
        
        if not target_package:
            target_package = config['package']
            print(f"Используется пакет из конфигурации: {target_package}")
        
        self.print_reverse_dependencies(target_package, config)
        print("Поиск обратных зависимостей завершен!")
    
    def run(self):
        parser = argparse.ArgumentParser(
            description='Инструмент визуализации графа зависимостей',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        parser.add_argument(
            '--config',
            type=str,
            required=True,
            help='Путь к конфигурационному файлу в формате CSV'
        )
        
        parser.add_argument(
            '--stage',
            type=int,
            choices=[1, 2, 3, 4, 5],
            default=1,
            help='Номер этапа для выполнения (1-5)'
        )
        
        try:
            args = parser.parse_args()
            
            print("Загрузка конфигурации...")
            config = self.load_config_from_csv(args.config)
            
            if args.stage >= 1:
                self.run_stage1(config)
            
            if args.stage >= 2:
                self.run_stage2(config)
            
            if args.stage >= 3:
                self.run_stage3(config)
            
            if args.stage >= 4:
                self.run_stage4(config)
                
        except Exception as e:
            print(f"Ошибка: {str(e)}", file=sys.stderr)
            sys.exit(1)


def main():
    if len(sys.argv) == 1:
        print("Использование: python dependency_visualizer.py --config <config_file.csv> [--stage N]")
        return
    
    visualizer = DependencyVisualizer()
    visualizer.run()

if __name__ == "__main__":
    main()