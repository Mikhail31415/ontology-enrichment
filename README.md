python version = 3.12

Основные зависимости окружения:
pip install pyyaml beautifulsoup4 owlready2 openai tiktoken

Для работы приложения необходимо чтобы в переменных среды была установленна переменная с именем OPENAI_API_KEY и значением вашего API ключа от OpenAI API

Для автоматической генерации промпта добавьте комментарий который начинается с "!" к классам индивидов которых вы хотите добавить, и свойствам, которые необходимо извлечь из текста. 
Можете дописать после "!" пояснение для модели о том что это свойство или класс значит, или другие инструкции по извлечению индивидов этого класса или добавлению этого свойства.

Если же вы хотите отправить свой промпт, запросите вернуть результат в виде структуры:
{ 
    “objects”: 
         {
              [“class name”, “object name”, “object metadata / additional data”, “object metadata / additional data” …], …
         }
                                                       
    “object properties”: 
         {
              [“property name”, “subject name”, “object name”], …      
         }

     “data properties”: 
         {
              [“property name”, “object name”, “value”], …      
         }
}
