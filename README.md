# 📋 Menaxhimi i Ankesave - Versioni 2.0

Aplikacion i plotë me file upload, fusha të reja dhe authentication.

## 🆕 Ndryshimet në Versionin 2.0

### Fusha të Reja:
- ✅ Nr. i Protokollit
- ✅ Titulli i Aktivitetit
- ✅ Lloji i Angazhimit (Ekspert Shqyrtues / Ekspert Teknik)
- ✅ Eksperti Shqyrtues (dinamik bazuar në llojin)
- ✅ OE Ankues (zëvendëson "Operatori Ekonomik Ankues")
- ✅ Nr. i Faturës
- ✅ Bashkëngjit Raportin (file upload)
- ✅ Bashkëngjit Vendimin (file upload)

### Funksionalitete të Reja:
- ✅ Auto-kalkulim: Shqyrtimi në ditë
- ✅ File upload në Supabase Storage
- ✅ Logjikë dinamike për Ekspert Shqyrtues/Teknik
- ✅ Login/Logout system
- ✅ Session management

---

## 🚀 SETUP I RI - HAPA SHTESË

### **PARA SE TË DEPLOY-OSH:**

Duhet të krijosh një **Storage Bucket** në Supabase për file uploads.

---

## 📦 KRIJIMI I SUPABASE STORAGE BUCKET

### Hapi 1: Hap Supabase Dashboard
- Shko te: https://supabase.com/dashboard
- Zgjedh projektin tënd

### Hapi 2: Krijo Bucket
1. Nga menuja majtas, kliko **Storage**
2. Kliko **"Create a new bucket"** (butoni jeshil)
3. Mbush:
   - **Name**: `ankesa-bucket`
   - **Public bucket**: ✅ **CHECKED** (shumë e rëndësishme!)
   - **File size limit**: 50MB (default)
   - **Allowed MIME types**: Leave empty (të gjitha llojet)
4. Kliko **"Create bucket"**

### Hapi 3: Krijo Folder brenda Bucket
1. Kliko mbi `ankesa-bucket` që sapo krijove
2. Kliko **"Create folder"**
3. Emri: `ankesa-files`
4. Kliko **"Create"**

### Hapi 4: Vendos RLS Policies (Row Level Security)
1. Në `ankesa-bucket`, kliko **"Policies"** tab
2. Kliko **"New Policy"**
3. Zgjedh **"For full customization"**
4. Template: **"Enable read access for all users"**
5. Emri: `Public read access`
6. Policy definition:
   ```sql
   true
   ```
7. Kliko **"Review"** → **"Save policy"**

8. **Krijo një tjetër policy për upload:**
   - Kliko **"New Policy"** përsëri
   - Zgjedh **"For full customization"**
   - Emri: `Public upload access`
   - Allowed operation: **INSERT**
   - Target roles: **public**
   - Policy definition:
     ```sql
     true
     ```
   - Kliko **"Save policy"**

---

## ✅ VERIFIKIM

Për të verifikuar që bucket-i funksionon:
1. Në Supabase Storage, kliko mbi `ankesa-bucket`
2. Provo të upload-osh një file test (Upload → Choose file)
3. Nëse sukses → Gati! ✅

---

## 🔧 DEPLOYMENT NË RENDER

### Hapi 1: Update GitHub Repository
1. **Fshi të gjithë skedarët e vjetër** në GitHub repository
2. **Upload të gjithë skedarët e rinj** nga `ankesa-app-v2`

### Hapi 2: Render do të Re-deploy Automatikisht
- Prit 2-3 minuta
- Kontrollo logs në Render dashboard

### Hapi 3: Testo Aplikacionin
1. Hap: https://ankesa-app.onrender.com/
2. Login: `admin` / `admin123`
3. Provo të regjistro

sh një ankesë me file upload

---

## 🔐 KREDENCIALET DEFAULT

**Username:** admin  
**Password:** admin123

⚠️ **Ndryshoje password menjëherë!**

---

## 📱 SI FUNKSIONON FILE UPLOAD

1. Gjatë regjistrimil, zgjedh file për Raport ose Vendim
2. Kur klikon "Ruaj", files upload-ohen automatikisht në Supabase
3. Progress bar tregon statusin e upload
4. URL e file ruhet në database
5. Në listën e ankesave, kliko mbi file për ta hapur

---

## ⚠️ PROBLEME TË MUNDSHME

### "Upload failed" ose "403 Forbidden"
- Sigurohu që bucket `ankesa-bucket` është **Public**
- Kontrollo RLS policies (duhet të jenë `true`)

### "Bucket not found"
- Emri i bucket duhet të jetë saktësisht `ankesa-bucket`
- Kontorllo typo në emër

### Files nuk hapen
- Sigurohu që RLS policy për READ është enabled
- Kontrollo që URL është publike

---

## 🎯 KARAKTERISTIKAT E PLOTA

### Regjistrim:
- 16 fusha (8 të detyrueshme)
- File upload për 2 dokumente
- Auto-kalkulim për ditët
- Validim dinamik

### Lista:
- 20 kolona
- Filtrim dhe kërkim
- Link direkt për files
- Eksport Excel
- Print

### Raporte:
- Statistika live
- Raporte mujore
- Totalizime automatike

---

## 🆘 SUPPORT

Nëse ke probleme:
1. Shiko Render logs
2. Shiko Supabase Storage logs
3. Verifyko që bucket është public

---

**Krijuar me ❤️ për menaxhim profesional**
