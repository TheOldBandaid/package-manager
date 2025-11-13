import argparse
import sys
import os
from typing import Dict, Any

class DependencyVisualizer:
    def __init__(self):
        self.config = {}
        
    def load_config_from_csv(self, config_file: str) -> Dict[str, Any]:
        config = {}
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if ';' in line:
                            key, value = line.split(';', 1)
                        else:
                            key, value = line.split(',', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if value.lower() in ['true', 'false']:
                            value = value.lower() == 'true'
                        elif value.isdigit():
                            value = int(value)
                            
                        config[key] = value
                        
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
        
        try:
            args = parser.parse_args()
            
            print("Загрузка конфигурации...")
            config = self.load_config_from_csv(args.config)
            
            print("Валидация параметров...")
            self.validate_config(config)
            
            self.print_config(config)
            
            print("Конфигурация успешно загружена и валидирована!")
            
        except Exception as e:
            print(f"Ошибка: {str(e)}", file=sys.stderr)
            sys.exit(1)


def main():
    if len(sys.argv) == 1:
        print("Использование: python dependency_visualizer.py --config <config_file.csv>")
        return
    
    visualizer = DependencyVisualizer()
    visualizer.run()

if __name__ == "__main__":
    main()