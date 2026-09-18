# 📸 Google Photos ReVanced (Bản Windows)

> **Sao lưu Ảnh & Video chất lượng gốc trọn đời KHÔNG GIỚI HẠN DUNG LƯỢNG cho Windows 10/11 nhờ cơ chế giả lập Google Pixel XL.**  
> Lưu trữ không giới hạn chất lượng gốc mà không trừ vào 15GB Google Drive / Google One.

---

<p align="center">
  <a href="README.md"><strong>🇺🇸 Read English Version (Bản tiếng Anh)</strong></a> &nbsp;|&nbsp; 
  <a href="README_VI.md"><strong>🇻🇳 Tiếng Việt (Hiện tại)</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/N%E1%BB%81n%20t%E1%BA%A3ng-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10/11" />
  <img src="https://img.shields.io/badge/Dung%20l%C6%B0%E1%BB%A3ng-Pixel%20XL%20Kh%C3%B4ng%20gi%E1%BB%9Bi%20h%E1%BA%A1n-22c55e?style=for-the-badge&logo=googlephotos&logoColor=white" alt="Pixel XL Unlimited" />
  <img src="https://img.shields.io/badge/M%E1%BA%A1ng-S%E1%BA%B5n%20s%C3%A0ng%201Gbps-f59e0b?style=for-the-badge&logo=speedtest&logoColor=white" alt="1Gbps Ready" />
  <img src="https://img.shields.io/badge/%C4%90a%20lu%E1%BB%93ng-L%C3%AAn%20%C4%91%E1%BA%BFn%2016%20lu%E1%BB%93ng-38bdf8?style=for-the-badge&logo=speedtest&logoColor=white" alt="Multi-Threaded" />
  <img src="https://img.shields.io/badge/Python-3.10%20--%203.14-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10 - 3.14" />
  <img src="https://img.shields.io/badge/Gi%E1%BA%A5y%20ph%C3%A9p-MIT-purple?style=for-the-badge" alt="MIT License" />
</p>

---

## ⚡ Cài đặt & Khởi chạy 1 bước duy nhất (Zero-Config)

Bạn chỉ cần có **Git** và **Python** (hoặc để trình khởi chạy tự tải và cài Python nếu máy chưa có):

```cmd
git clone https://github.com/kingbone2006/GPhotosReVanced-Windows.git
cd GPhotosReVanced-Windows
run.bat
```

> [!TIP]
> **Chỉ cần nhấp đúp vào `run.bat`:**
> 1. Tự động nhận diện Python (hoặc tự động cài Python 3.11 nếu máy chưa có).
> 2. Tự động khởi tạo môi trường ảo độc lập (`venv`).
> 3. Tự động cài đặt toàn bộ thư viện từ `requirements.txt`.
> 4. Khởi động phần mềm ngay lập tức. Các lần mở sau ứng dụng sẽ khởi động trong vòng 1 giây!

---

## 📑 Mục lục
- [🌟 Tính năng nổi bật](#-tính-năng-nổi-bật)
- [⚡ Cài đặt & Khởi chạy 1 bước](#-cài-đặt--khởi-chạy-1-bước-duy-nhất-zero-config)
- [🛠️ Hướng dẫn cài đặt thủ công](#️-hướng-dẫn-cài-đặt-thủ-công)
- [🚀 Hướng dẫn sử dụng nhanh từ A-Z](#-hướng-dẫn-sử-dụng-nhanh-từ-a-z)
- [⚙️ Cấu hình luồng & Kiến trúc tăng tốc tối đa](#️-cấu-hình-luồng--kiến-trúc-tăng-tốc-tối-đa)
- [🗂️ Tính năng tự động tạo Album theo thư mục (Auto-Album)](#️-tính-năng-tự-động-tạo-album-theo-thư-mục-auto-album)
- [🌐 Hỗ trợ song ngữ (Tiếng Anh & Tiếng Việt)](#-hỗ-trợ-song-ngữ-tiếng-anh--tiếng-việt)
- [🔒 Cam kết bảo mật & Quyền riêng tư](#-cam-kết-bảo-mật--quyền-riêng-tư)
- [❓ Các câu hỏi thường gặp (FAQ)](#-các-câu-hỏi-thường-gặp-faq)
- [📄 Giấy phép & Tuyên bố miễn trừ trách nhiệm](#-giấy-phép--tuyên-bố-miễn-trừ-trách-nhiệm)

---

## 🌟 Tính năng nổi bật

- **📱 Giả lập phần cứng Pixel XL**: Xác thực trực tiếp với API Google Photos bằng thông số định danh Google Pixel XL (`marlin`), mở khoá đặc quyền sao lưu **chất lượng gốc vĩnh viễn cho cả Ảnh và Video** mà không tính dung lượng Google Drive.
- **🚀 Đường ống đệm RAM Cache (In-Memory Pipeline)**: Đọc trước dữ liệu vào RAM theo luồng đọc tuần tự của ổ đĩa, triệt tiêu hoàn toàn hiện tượng nghẽn đầu từ HDD (Head Thrashing), đưa thời gian bận đĩa về mức thấp và đẩy băng thông upload lên tối đa (**40 – 80+ MB/s**).
- **⚡ Băm SHA-1 đa nhân CPU**: Đẩy tính toán hàm băm SHA-1 sang tiến trình đa nhân CPU chạy song song, vượt qua rào cản Python GIL và đạt tốc độ băm lên tới ~2.500 MB/s.
- **🌐 Tối ưu hóa mạng 1Gbps**: Tái sử dụng phiên kết nối HTTP/TLS 1.3 Keep-Alive, kích hoạt `TCP_NODELAY`, bộ đệm Winsock 2MB và khối truyền 1MB giúp tận dụng trọn vẹn đường truyền cáp quang.
- **🔄 Tự động giám sát thư mục theo thời gian thực (Auto-Sync)**: Theo dõi liên tục các thư mục trên máy tính. Bất cứ khi nào bạn sao chép thêm ảnh/video mới vào, ứng dụng sẽ tự động sao lưu ngầm lên Google Photos.
- **🗂️ Tự động gom nhóm Album theo tên thư mục (Auto-Album)**: Phân loại thông minh ảnh trên đám mây theo cấu trúc thư mục trên ổ cứng, tự phục hồi nếu album bị xoá và phân tách độc lập giữa các tài khoản.
- **🔐 Đăng nhập 1-Click tự bắt Token**: Sử dụng Chrome DevTools Protocol (CDP) tự động ghi nhận token khi đăng nhập trong cửa sổ an toàn của Google—hoàn toàn không cần thao tác thủ công.
- **🎨 Giao diện Fluent Dark phong cách Windows 11**: Thiết kế hiện đại bằng CustomTkinter, tích hợp khay thẻ tải ảnh mô phỏng Google Photos Android với hiệu ứng biến mất khi tải xong.
- **🌐 Tuỳ chọn ngôn ngữ linh hoạt**: Tiếng Anh mặc định, chuyển đổi tức thì sang Tiếng Việt ngay trong phần Cài đặt mà không cần khởi động lại ứng dụng.

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
3. Đăng nhập tài khoản Google của bạn trong cửa sổ trình duyệt và bấm **"Tôi đồng ý"**.
4. Ứng dụng tự động thu thập token, kích hoạt hồ sơ Pixel XL và đóng cửa sổ.

### Bước 2: Thiết lập thư mục ảnh & video
1. Chọn tab **📁 Thư mục đồng bộ**.
2. Nhấn **➕ Thêm thư mục** để chọn các nơi lưu trữ ảnh/video (ví dụ: `Pictures`, `DCIM`, thư mục sao lưu từ điện thoại).
3. Bật tuỳ chọn **"Tự động tạo Album theo tên thư mục"** nếu muốn tự gom nhóm ảnh trên Google Photos.
4. Bấm **🔄 Quét tất cả thư mục ngay** để đưa toàn bộ tệp hiện có vào hàng đợi sao lưu.

### Bước 3: Theo dõi tiến trình tải lên
- Tab **📊 Bảng điều khiển** hiển thị trực quan từng thẻ file đang tải với tiến độ % và tốc độ MB/s thời gian thực.
- Khi tải hoàn tất, các thẻ sẽ tự động mượt mà biến mất tương tự ứng dụng Google Photos trên điện thoại Android.

---

## ⚙️ Cấu hình luồng & Kiến trúc tăng tốc tối đa

| Số luồng | Trường hợp khuyên dùng |
| :--- | :--- |
| **2 luồng** | Ổ cứng cơ HDD SATA tốc độ thấp hoặc đường truyền mạng chậm. |
| **4 – 6 luồng (Khuyên dùng)** | Mạng cáp quang gia đình tiêu chuẩn (100Mbps – 500Mbps); cân bằng hoàn hảo, không bị Google rate limit. |
| **8 – 12 luồng** | Đường truyền cáp quang Gigabit (1Gbps) kết hợp ổ SSD hoặc cơ chế RAM Cache. |
| **16 luồng (Cực đại)** | Hệ thống CPU nhiều nhân mạnh mẽ, ổ NVMe SSD và dung lượng RAM dồi dào. |

> [!TIP]
> **Cơ chế RAM Cache giải quyết nghẽn đĩa HDD cơ như thế nào?**  
> Khi chạy đồng thời nhiều luồng trên ổ HDD cơ, đầu từ đọc bị giật ngẫu nhiên khiến tốc độ đọc rơi xuống 2 MB/s. Hệ thống tự động giới hạn đọc đĩa tuần tự tối đa 2 luồng với khối 4MB vào RAM, sau đó các luồng upload mạng sẽ truyền thẳng từ RAM ra mạng với tốc độ tối đa của đường truyền (40 – 80+ MB/s).

---

## 🗂️ Tính năng tự động tạo Album theo thư mục (Auto-Album)

Khi bật **Auto-Album**:
- Ảnh nằm tại `D:\Photos\Du Lịch Đà Nẵng 2025\IMG_001.jpg` sẽ tự động được thêm vào album mang tên `Du Lịch Đà Nẵng 2025` trên Google Photos.
- Hệ thống tự động kiểm tra album trên tài khoản để chống tạo trùng lặp.
- Nếu album bị bạn xoá trên Google Photos, ứng dụng sẽ tự động phát hiện mã `404 Not Found` và khởi tạo lại album mới một cách trong suốt.
- Hỗ trợ nhiều tài khoản độc lập hoàn toàn với khoá lưu trữ `(account_email, album_name)`.

---

## 🌐 Hỗ trợ song ngữ (Tiếng Anh & Tiếng Việt)

Ứng dụng hỗ trợ chuyển đổi ngôn ngữ tức thì:
1. Mở tab **⚙️ Cài đặt**.
2. Chọn **Tiếng Việt** trong ô **Ngôn ngữ giao diện**.
3. Toàn bộ các tab, nút bấm, thông báo trạng thái sẽ lập tức chuyển đổi sang tiếng Việt mà không cần khởi động lại app.

---

## 🔒 Cam kết bảo mật & Quyền riêng tư

- **Kết nối trực tiếp**: Mọi yêu cầu mạng đều kết nối trực tiếp đến máy chủ chính thức của Google (`photoslibrary.googleapis.com`, `play.googleapis.com`, `accounts.google.com`).
- **Không qua trung gian**: Tài khoản, mật khẩu, token và dữ liệu hình ảnh của bạn không bao giờ gửi qua bất kỳ máy chủ bên thứ ba nào.
- **Lưu trữ cục bộ**: Token xác thực và cơ sở dữ liệu lịch sử tải được lưu trên máy của bạn tại `%LOCALAPPDATA%\GPhotosReVanced\`.
- **An toàn tuyệt đối cho Cloud**: Việc đặt lại thống kê (Reset Stats) hoặc xoá lịch sử local hoàn toàn không ảnh hưởng hay làm mất ảnh đã tải lên Google Photos.

---

## ❓ Các câu hỏi thường gặp (FAQ)

#### Q: Có thật sự không giới hạn dung lượng Google Drive không?
**A:** Hoàn toàn chính xác. Google cấp đặc quyền miễn phí trọn đời chất lượng gốc cho thiết bị Google Pixel thế hệ đầu (2016). Ứng dụng giả lập chuẩn xác chữ ký thiết bị Pixel XL (`marlin`), cho phép mọi ảnh và video tải lên hoàn toàn không bị trừ vào 15GB Google One của bạn.

#### Q: Những định dạng media nào được hỗ trợ?
**A:** Đầy đủ các định dạng phổ biến:
- **Ảnh thông thường**: `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.bmp`, `.gif`, `.tiff`
- **Ảnh RAW máy ảnh**: `.dng`, `.cr2`, `.nef`, `.arw`, `.rw2`, `.orf`
- **Video**: `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.3gp`, `.m4v`, `.mts`

#### Q: Có thể cho phần mềm tự chạy ẩn ngầm khi khởi động Windows không?
**A:** Hoàn toàn được. Bạn chỉ cần tạo lối tắt (shortcut) của file `run_silent.vbs` và đưa vào thư mục Startup của Windows (bấm `Win + R`, nhập `shell:startup` rồi dán shortcut vào).

---

## 📄 Giấy phép & Tuyên bố miễn trừ trách nhiệm

- Dự án mã nguồn mở này được phát triển phục vụ mục đích sao lưu cá nhân phi thương mại và nghiên cứu kỹ thuật.
- Google Photos là thương hiệu đã đăng ký của Google LLC. Dự án không thuộc sở hữu hoặc liên kết chính thức với Google LLC.
- Được phát hành theo giấy phép **[MIT License](LICENSE)**.
