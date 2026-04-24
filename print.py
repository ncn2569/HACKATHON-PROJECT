import os

# 1. Khai báo các thư mục và file MẬT hoặc RÁC cần bỏ qua
IGNORE_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', '.idea', '.vscode','.csv', '.jsonl','json'}
IGNORE_FILES = {'.env', '.env.example', 'gom_code.py', 'all_code.txt', 'requirements.txt','data-cleaned.jsonl','print.py'}

# 2. (Tùy chọn) Chỉ định các đuôi file muốn gom để tránh đọc nhầm file ảnh, model AI...
ALLOWED_EXTENSIONS = {'.py', '.md', '.txt','.gitignore'}

output_filename = 'all_code.txt'

print("Đang tiến hành gom code...")

# Mở file kết quả với chuẩn UTF-8
with open(output_filename, 'w', encoding='utf-8') as outfile:
    for root, dirs, files in os.walk('.'):
        # Bỏ qua các thư mục trong IGNORE_DIRS
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if file in IGNORE_FILES:
                continue

            # Bỏ qua nếu không phải đuôi file code
            if not any(file.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                continue

            filepath = os.path.join(root, file)
            
            try:
                # ĐỌC FILE: Dùng errors='replace' để nếu có ký tự dị dạng nó sẽ tự thay bằng dấu '?', KHÔNG BAO GIỜ BỊ CRASH
                with open(filepath, 'r', encoding='utf-8', errors='replace') as infile:
                    content = infile.read()
                    
                    # Ghi tên file làm tiêu đề cho AI dễ đọc
                    outfile.write(f"\n{'='*50}\n")
                    outfile.write(f"FILE: {filepath}\n")
                    outfile.write(f"{'='*50}\n\n")
                    
                    outfile.write(content)
                    outfile.write("\n")
            except Exception as e:
                print(f" Không thể đọc file {filepath}: {e}")

print(f" Đã gom code thành công vào file: {output_filename} (Không lỗi font!)")