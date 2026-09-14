# 📸 Google Photos ReVanced (Bản Windows)

> **Sao lưu Ảnh & Video chất lượng gốc trọn đời KHÔNG GIỚI HẠN DUNG LƯỢNG cho Windows 10/11 nhờ cơ chế giả lập Google Pixel XL.**

---

<p align="center">
  <a href="README.md"><strong>🇺🇸 Read English Version (Bản tiếng Anh)</strong></a> &nbsp;|&nbsp; 
  <a href="README_VI.md"><strong>🇻🇳 Tiếng Việt (Hiện tại)</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/N%E1%BB%81n%20t%E1%BA%A3ng-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10/11" />
  <img src="https://img.shields.io/badge/Dung%20l%C6%B0%E1%BB%A3ng-Pixel%20XL%20Kh%C3%B4ng%20gi%E1%BB%9Bi%20h%E1%BA%A1n-22c55e?style=for-the-badge&logo=googlephotos&logoColor=white" alt="Pixel XL Unlimited" />
  <img src="https://img.shields.io/badge/%C4%90a%20lu%E1%BB%93ng-L%C3%AAn%20%C4%91%E1%BA%BFn%208%20lu%E1%BB%93ng-38bdf8?style=for-the-badge&logo=speedtest&logoColor=white" alt="Multi-Threaded" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Gi%E1%BA%A5y%20ph%C3%A9p-MIT-purple?style=for-the-badge" alt="MIT License" />
</p>

---

## 📑 Mục lục
- [🌟 Tính năng nổi bật](#-tính-năng-nổi-bật)
- [⚡ Cài đặt tự động 1-Click trên máy bất kỳ](#-cài-đặt-tự-động-1-click-trên-máy-bất-kỳ)
- [🛠️ Hướng dẫn cài đặt thủ công](#️-hướng-dẫn-cài-đặt-thủ-công)
- [🚀 Hướng dẫn sử dụng nhanh từ A-Z](#-hướng-dẫn-sử-dụng-nhanh-từ-a-z)
- [⚙️ Cấu hình và Tối ưu hoá số luồng tải](#️-cấu-hình-và-tối-ưu-hoá-số-luồng-tải)
- [🗂️ Tính năng tự động tạo Album theo thư mục (Auto-Album)](#️-tính-năng-tự-động-tạo-album-theo-thư-mục-auto-album)
- [🌐 Hỗ trợ song ngữ (Tiếng Anh & Tiếng Việt)](#-hỗ-trợ-song-ngữ-tiếng-anh--tiếng-việt)
- [🔒 Cam kết bảo mật & Quyền riêng tư](#-cam-kết-bảo-mật--quyền-riêng-tư)
- [❓ Các câu hỏi thường gặp (FAQ)](#-các-câu-hỏi-thường-gặp-faq)
- [📄 Giấy phép & Tuyên bố miễn trừ trách nhiệm](#-giấy-phép--tuyên-bố-miễn-trừ-trách-nhiệm)

---

## 🌟 Tính năng nổi bật

- **📱 Giả lập phần cứng Pixel XL**: Xác thực trực tiếp với API Google Photos bằng thông số định danh Google Pixel XL (`marlin`), mở khoá đặc quyền sao lưu chất lượng gốc miễn phí vĩnh viễn mà không trừ vào 15GB Google One / Google Drive của bạn.
- **⚡ Động cơ tải đa luồng siêu tốc**: Cho phép tải lên đồng thời nhiều ảnh và video (hỗ trợ lên đến 8 luồng song song), khai thác tối đa băng thông đường truyền internet.
- **🔄 Tự động giám sát thư mục theo thời gian thực (Auto-Sync)**: Theo dõi liên tục các thư mục trên máy tính. Bất cứ khi nào bạn sao chép thêm ảnh/video mới vào, ứng dụng sẽ tự động tải lên Google Photos trong nền.
- **🗂️ Tự động gom nhóm Album theo tên thư mục (Auto-Album)**: Phân loại thông minh ảnh trên đám mây theo cấu trúc thư mục trên ổ cứng, có cơ chế tự phục hồi nếu album bị xoá và phân tách độc lập giữa các tài khoản.
- **🔐 Đăng nhập 1-Click tự bắt Token**: Sử dụng giao thức Chrome DevTools Protocol (CDP) tự động ghi nhận `oauth_token` khi đăng nhập trong cửa sổ an toàn của Google—hoàn toàn không cần mở F12 hay làm thao tác thủ công.
- **🎨 Giao diện Fluent Dark phong cách Windows 11**: Thiết kế hiện đại bằng CustomTkinter, tích hợp khay thẻ tải ảnh mô phỏng Google Photos Android với hiệu ứng biến mất khi tải xong.
- **🌐 Tuỳ chọn ngôn ngữ linh hoạt**: Tiếng Anh làm mặc định, chuyển đổi tức thì sang Tiếng Việt ngay trong phần Cài đặt mà không cần khởi động lại ứng dụng.
- **🔄 Quản trị thống kê dữ liệu**: Hiển thị số ảnh đã sao lưu và dung lượng tiết kiệm theo thời gian thực, tích hợp nút Reset đặt lại thống kê về 0 bất cứ lúc nào.

---

## ⚡ Cài đặt tự động 1-Click trên máy bất kỳ

Dễ dàng cài đặt và vận hành trên **bất kỳ máy tính Windows nào** mà không đòi hỏi thao tác kỹ thuật phức tạp:

1. **Tải về hoặc Clone mã nguồn**:
   ```cmd
   git clone https://github.com/kingbone2006/GPhotosReVanced-Windows.git
   cd GPhotosReVanced-Windows
   ```

2. **Chạy file `install.bat`**:
   - Nhấp đúp chuột vào `install.bat`.
   - Trình cài đặt tự động thực hiện tất cả các bước:
     - Kiểm tra Python (tự động tải và cài đặt bản Python 3.11 chính thức qua `winget` hoặc web nếu máy chưa có).
     - Khởi tạo môi trường ảo độc lập (`venv`).
     - Nâng cấp `pip` và tự động cài đủ toàn bộ thư viện từ `requirements.txt`.
     - Tự động tạo biểu tượng ngoài màn hình Desktop (`Google Photos ReVanced.lnk`).

3. **Khởi chạy phần mềm**:
   - Chạy `run.bat` (chế độ cửa sổ debug để theo dõi nhật ký tải) hoặc `run_silent.vbs` (chạy ẩn ngầm không hiện màn hình đen).
   - *(Lưu ý: Nếu bạn mở trực tiếp `run.bat` lần đầu, chương trình sẽ tự động kích hoạt `install.bat` cho bạn!)*

---

## 🛠️ Hướng dẫn cài đặt thủ công

Nếu bạn muốn tự thiết lập từng bước:

```cmd
# 1. Clone repository
git clone https://github.com/kingbone2006/GPhotosReVanced-Windows.git
cd GPhotosReVanced-Windows

# 2. Tạo và kích hoạt môi trường ảo Python
python -m venv venv
call venv\Scripts\activate

# 3. Cài đặt các thư viện phụ thuộc
pip install --upgrade pip
pip install -r requirements.txt

# 4. Khởi động ứng dụng
python main.py
```

---

## 🚀 Hướng dẫn sử dụng nhanh từ A-Z

### Bước 1: Kết nối tài khoản Google
1. Bấm nút **"Connect Account"** (hoặc **"Kết nối tài khoản"**) ở góc trên bên phải giao diện.
2. Chọn tab **"⚡ Đăng nhập tự động 1-Click (Khuyên dùng)"** và nhấn **"Mở cửa sổ đăng nhập Google"**.
3. Điền thông tin tài khoản Google của bạn và nhấn **"I agree"** (Tôi đồng ý) khi được hỏi.
4. Ứng dụng sẽ tự động ghi nhận mã token, cấp quyền giả lập Pixel XL và sẵn sàng sao lưu.

### Bước 2: Thiết lập thư mục cần đồng bộ
1. Chọn tab **📁 Thư mục đồng bộ** (Sync Folders).
2. Nhấn **➕ Thêm thư mục theo dõi** để chọn các thư mục chứa ảnh và video (như `Pictures`, ảnh máy ảnh, ảnh điện thoại chép vào PC...).
3. Bật tuỳ chọn **"Tự động tạo Album theo tên thư mục"** nếu muốn giữ nguyên phân loại album trên Google Photos.
4. Nhấn **🔄 Quét toàn bộ thư mục ngay** để đưa các file có sẵn vào hàng đợi sao lưu.

### Bước 3: Theo dõi quá trình sao lưu
- Tab **📊 Bảng điều khiển** hiển thị trực quan các luồng tải đang chạy cùng thanh tiến trình và tốc độ mạng.
- Tải xong file nào, thẻ file đó sẽ hiển thị dấu tích xanh và tự động thu nhỏ biến mất.

---

## ⚙️ Cấu hình và Tối ưu hoá số luồng tải

| Số luồng (Threads) | Trường hợp sử dụng khuyến nghị |
| :--- | :--- |
| **1 - 2 luồng** | Mạng yếu, kết nối dữ liệu di động hoặc muốn để app chạy ngầm khi chơi game. |
| **4 luồng (Mặc định)** | Cân bằng lý tưởng nhất giữa tốc độ và độ ổn định cho mạng gia đình thông thường. |
| **6 luồng (Siêu tốc)** | Đường truyền cáp quang tốc độ cao (100Mbps trở lên), tải nhanh video dung lượng lớn. |
| **8 luồng (Tối đa)** | Mạng Internet Gigabit; đẩy tối đa băng thông tải lên. |

Bạn có thể thay đổi số luồng tải ngay lập tức trên thanh công cụ Bảng điều khiển hoặc trong tab Cài đặt.

---

## 🗂️ Tính năng tự động tạo Album theo thư mục (Auto-Album)

Khi bật **Auto-Album**:
- Ảnh lưu tại `D:\Anh_Du_Lich\Da_Lat_2025\IMG_001.jpg` sẽ tự động được thêm vào Album mang tên `Da_Lat_2025` trên Google Photos.
- Ứng dụng tự động kiểm tra xem album đã tồn tại trên Cloud hay chưa để tránh tạo trùng lặp.
- Nếu album bị xoá trên Google Photos, ứng dụng sẽ phát hiện và tự động tạo lại album mới.
- Hỗ trợ lưu trữ dữ liệu an toàn riêng biệt cho từng tài khoản qua cơ chế khoá kép `(account_email, album_name)`.

---

## 🌐 Hỗ trợ song ngữ (Tiếng Anh & Tiếng Việt)

Phần mềm thiết lập mặc định là **Tiếng Anh (English)**. Bạn có thể chuyển sang **Tiếng Việt** bất cứ lúc nào:
1. Mở tab **⚙️ Cài đặt** (Settings).
2. Tại mục **Ngôn ngữ giao diện** (Interface Language), chọn **Tiếng Việt**.
3. Toàn bộ các thẻ, nút bấm và thông báo sẽ lập tức chuyển sang Tiếng Việt.

---

## 🔒 Cam kết bảo mật & Quyền riêng tư

- **Kết nối trực tiếp**: Mọi yêu cầu kết nối mạng đều gửi trực tiếp đến hệ thống máy chủ chính thức của Google (`photoslibrary.googleapis.com`, `play.googleapis.com`, `accounts.google.com`).
- **Không qua máy chủ trung gian**: Tuyệt đối không gửi tài khoản, mật khẩu, token hay ảnh của bạn qua bất kỳ bên thứ ba nào.
- **Lưu trữ bảo mật cục bộ**: Toàn bộ dữ liệu token và lịch sử sao lưu được lưu trữ trên máy tính của bạn tại `%LOCALAPPDATA%\GPhotosReVanced\`.
- **An toàn tuyệt đối cho Cloud**: Việc xoá lịch sử hoặc reset thống kê trên app chỉ xoá dữ liệu theo dõi trên máy tính, không bao giờ làm mất ảnh hay album đã tải lên tài khoản Google Photos.

---

## ❓ Các câu hỏi thường gặp (FAQ)

#### Q: Sao lưu bằng ứng dụng này có thật sự không tốn dung lượng Google Drive?
**A:** Hoàn toàn chính xác. Google cấp đặc quyền sao lưu chất lượng gốc miễn phí không giới hạn trọn đời cho thiết bị Google Pixel thế hệ đầu (2016). Bằng việc giả lập chuẩn xác chữ ký thiết bị và tham số phần cứng Pixel XL, toàn bộ ảnh/video bạn tải lên sẽ không bị tính vào 15GB dung lượng tài khoản.

#### Q: Ứng dụng hỗ trợ những định dạng file nào?
**A:** Hỗ trợ đầy đủ tất cả định dạng đa phương tiện phổ biến:
- **Ảnh thông dụng**: `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.bmp`, `.gif`, `.tiff`
- **Ảnh RAW chuyên nghiệp**: `.dng`, `.cr2`, `.nef`, `.arw`, `.rw2`, `.orf`
- **Video**: `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.3gp`, `.m4v`

#### Q: Làm thế nào để ứng dụng tự chạy ngầm cùng Windows?
**A:** Bạn chỉ cần tạo shortcut của file `run_silent.vbs` và đặt vào thư mục khởi động của Windows (nhấn `Win + R`, gõ `shell:startup` và nhấn Enter).

---

## 📄 Giấy phép & Tuyên bố miễn trừ trách nhiệm

- Dự án mã nguồn mở này được phát triển cho mục đích học tập, nghiên cứu và sao lưu dữ liệu cá nhân phi thương mại.
- Google Photos là thương hiệu của Google LLC. Dự án này hoàn toàn độc lập và không liên kết hay được chứng thực bởi Google LLC.
- Phát hành theo giấy phép bản quyền mở **MIT License**.
