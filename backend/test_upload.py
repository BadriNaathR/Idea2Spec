# Sample Python Code
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b

def main():
    calc = Calculator()
    print(calc.add(5, 3))

if __name__ == "__main__":
    main()
