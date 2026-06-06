# MigraDiff

<div align="center">

**भाषा चुनें:**  
[English](README.md) | 
[हिन्दी](README.hi.md) | 
[中文](README.zh.md) | 
[日本語](README.ja.md) | 
[Français](README.fr.md) | 
[Deutsch](README.de.md) | 
[עברית](README.he.md)

</div>

---

# migra — PostgreSQL स्कीमा डिफ टूल

[![PyPI version](https://img.shields.io/pypi/v/migradiff)](https://pypi.org/project/migradiff/)
[![Python versions](https://img.shields.io/pypi/pyversions/migradiff)](https://pypi.org/project/migradiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**यह [djrobstep/migra](https://github.com/djrobstep/migra) का सक्रिय रूप से अनुरक्षित फोर्क है।**

migra दो PostgreSQL डेटाबेस स्कीमा की तुलना करता है और एक स्कीमा को दूसरे में बदलने के लिए आवश्यक SQL माइग्रेशन स्क्रिप्ट जनरेट करता है। इसे अपनी CI पाइपलाइन में शामिल करें और `ALTER TABLE` हाथ से लिखना बंद करें।

---

## यह फोर्क क्यों?

मूल `migra` को 2024 में आधिकारिक रूप से डिप्रीकेटेड घोषित किया गया था। यह फोर्क वहीं से शुरू होता है — ज्ञात समस्याओं को ठीक करना, Python 3.12+ सपोर्ट जोड़ना, और उन्नत PostgreSQL सुविधाओं के लिए कवरेज बढ़ाना।

यदि आप `djrobstep/migra` उपयोग कर रहे थे, तो यह आपका ड्रॉप-इन कंटीन्यूएशन है। टूल के काम करने के तरीके में कुछ भी नहीं बदला है। हम बस इसे चालू रख रहे हैं और बेहतर बना रहे हैं।

**नामकरण पर एक नोट:** यह एक स्वतंत्र सामुदायिक फोर्क है। CLI कमांड मौजूदा स्क्रिप्ट और पाइपलाइनों के साथ बैकवर्ड कम्पैटिबिलिटी के लिए `migra` ही रहता है। पैकेज का नाम `migradiff` है ताकि इसे डिप्रीकेटेड अपस्ट्रीम से अलग किया जा सके। यदि आप मूल djrobstep/migra खोज रहे हैं, तो यह https://github.com/djrobstep/migra पर आर्काइव है।

---

## त्वरित आरंभ

### इंस्टॉलेशन

```bash
pip install migradiff
```

इसके लिए Python 3.10+ और एक चालू PostgreSQL इंस्टेंस (12+) आवश्यक है।

स्रोत से इंस्टॉल करने के लिए:

```bash
git clone https://github.com/migradiff/migra
cd migra
pip install -e .
```

### मूल उपयोग

migra को दो डेटाबेस कनेक्शनों पर पॉइंट करें और यह एक से दूसरे में माइग्रेट करने के लिए आवश्यक DDL आउटपुट करेगा:

```bash
migra \
  postgresql://user:pass@localhost/db_production \
  postgresql://user:pass@localhost/db_branch \
  --unsafe
```

आउटपुट सादा SQL है — इसे पाइप करें, समीक्षा करें, लागू करें:

```bash
migra postgres://db_a postgres://db_b > migration.sql
psql postgres://db_production < migration.sql
```

### स्कीमा डंप (लाइव कनेक्शन आवश्यक नहीं)

यदि आप migra को लाइव डेटाबेस पर पॉइंट नहीं कर सकते या नहीं करना चाहते, तो `pg_dump -s` का उपयोग करके स्कीमा डंप जनरेट करें और उसके बजाय उसका डिफ करें:

```bash
pg_dump -s postgres://db_production > schema_a.sql
pg_dump -s postgres://db_branch     > schema_b.sql
migra --from-file schema_a.sql schema_b.sql
```

यह CI पाइपलाइनों और सुरक्षा-सचेत वातावरणों के लिए अनुशंसित तरीका है — कोई प्रोडक्शन क्रेडेंशियल आवश्यक नहीं।

### माइग्रेशन निर्देशिका (लाइव ब्रांच डेटाबेस आवश्यक नहीं)

यदि आपकी लक्ष्य स्थिति माइग्रेशन फ़ाइलों के फ़ोल्डर द्वारा परिभाषित है:

```bash
migra --from-migrations-dir ./migrations postgres://db_production
```

MigraDiff माइग्रेशन को एक एफेमेरल डेटाबेस पर लागू करता है और परिणाम का डिफ करता है। Supabase, Flyway, और मानक संख्यात्मक नामकरण परंपराओं का समर्थन करता है।

### एक स्कीमा तक सीमित

```bash
# एकल स्कीमा
migra --schema myschema postgres://db_a postgres://db_b

# एकाधिक स्कीमा (अल्पविराम-पृथक)
migra --schema public,reporting postgres://db_a postgres://db_b
```

### JSON आउटपुट

प्रोग्रामेटिक उपभोग या CI पाइपलाइनों के लिए:

```bash
migra --output json postgres://db_a postgres://db_b
```

आउटपुट में प्रति-स्टेटमेंट जोखिम वर्गीकरण (`safe`, `warning`, `destructive`) और समग्र जोखिम स्तर के साथ एक सारांश शामिल है।

---

## AI-संचालित स्पष्टीकरण (वैकल्पिक)

MigraDiff किसी भी माइग्रेशन को सादी अंग्रेजी में समझा सकता है — प्रत्येक परिवर्तन क्या करता है, इसमें क्या जोखिम हैं, और विनाशकारी संचालन के लिए सुरक्षित विकल्प।

    migra --explain postgres://db_a postgres://db_b

आउटपुट:

    --- Migration SQL ---
    ALTER TABLE public.users ADD COLUMN email text;
    DROP TABLE public.legacy_sessions;

    --- AI Explanation ---
    This migration makes 2 changes to your database:

    1. SAFE: Adds an email column (text) to the users table.
       No existing data is affected.

    2. ⚠ DESTRUCTIVE: Drops the legacy_sessions table entirely.
       All data in this table will be permanently lost.
       Consider archiving before dropping.

    Overall risk: HIGH

Claude (Anthropic) द्वारा संचालित। अपनी खुद की API कुंजी लाएं — MigraDiff सर्वरों को कोई डेटा नहीं भेजा जाता।

### सेटअप

AI एक्सट्रा इंस्टॉल करें:

    pip install migradiff[ai]

अपनी API कुंजी एक बार कॉन्फ़िगर करें:

    migra --setup-ai

या पर्यावरण चर सेट करें:

    export ANTHROPIC_API_KEY=sk-ant-...

https://console.anthropic.com पर API कुंजी प्राप्त करें।

### AI रोलबैक जनरेशन (--rollback)

सटीक रिवर्स माइग्रेशन जनरेट करें — किसी भी माइग्रेशन को पूर्ववत करने के लिए आवश्यक SQL:

    migra --rollback migration.sql
    migra --rollback postgres://db_a postgres://db_b

MigraDiff आपके स्रोत स्कीमा संदर्भ का उपयोग करके DROP TABLE और DROP COLUMN रिवर्सल को सटीक रूप से पुनर्निर्मित करता है। गैर-प्रतिवर्ती संचालन (TRUNCATE, bulk DELETE) स्पष्ट रूप से चिह्नित किए जाते हैं।

पूरी तस्वीर के लिए --explain के साथ संयोजित करें:

    migra --explain --rollback postgres://db_a postgres://db_b

इसके लिए `pip install migradiff[ai]` और Anthropic API कुंजी आवश्यक है।

### AI प्रदर्शन सलाहकार (--advise)

किसी भी माइग्रेशन को लागू करने से पहले, प्रदर्शन जोखिम मूल्यांकन प्राप्त करें — लॉकिंग व्यवहार, टेबल रीराइट जोखिम, और जीरो-डाउनटाइम विकल्प:

    migra --advise postgres://db_a postgres://db_b
    migra --advise migration.sql

MigraDiff प्रत्येक स्टेटमेंट का PostgreSQL-विशिष्ट जोखिमों के लिए विश्लेषण करता है: टेबल लॉक, पूर्ण रीराइट, अपरिवर्तनीय डेटा हानि। जब लाइव कनेक्शन प्रदान किया जाता है, तो आपके वास्तविक डेटा स्केल पर लॉक अवधि का अनुमान लगाने के लिए टेबल पंक्ति गणना का उपयोग किया जाता है।

पूरी तस्वीर के लिए तीनों AI सुविधाओं को संयोजित करें:

    migra --explain --advise --rollback postgres://db_a postgres://db_b

इसके लिए pip install migradiff[ai] और Anthropic API कुंजी आवश्यक है।

### AI माइग्रेशन जनरेटर (--generate)

आप जो चाहते हैं उसे सादी अंग्रेजी में बताएं — MigraDiff आपके वास्तविक स्कीमा पर आधारित माइग्रेशन SQL जनरेट करता है:

    migra --generate "add email verification to users table" \
      postgres://db_production

सामान्य AI टूल के विपरीत, MigraDiff आपके वास्तविक टेबल नाम, कॉलम प्रकार और बाधाओं को जानता है — कोई हेलुसिनेटेड कॉलम नाम या गलत प्रकार नहीं।

जनरेट करें और तुरंत जोखिम की समीक्षा करें:

    migra --generate "add index on orders.user_id" \
      --advise postgres://db_production

इसके लिए pip install migradiff[ai] और Anthropic API कुंजी आवश्यक है।

---

## डेवलपमेंट सेटअप

टेस्ट सूट के लिए एक चालू PostgreSQL इंस्टेंस आवश्यक है। इसे प्राप्त करने का सबसे आसान तरीका Docker Compose है:

```bash
docker compose up -d
```

यह लोकलहोस्ट:5432 पर ट्रस्ट प्रमाणीकरण के साथ एक Postgres 16 कंटेनर शुरू करता है। कोई पासवर्ड आवश्यक नहीं।

इसे रोकने के लिए:

```bash
docker compose down
```

डेटा `migradiff-pgdata` वॉल्यूम के माध्यम से रीस्टार्ट के बीच बना रहता है। पूरी तरह से रीसेट करने के लिए:

```bash
docker compose down -v
```

---

## Docker

कोई Python वातावरण नहीं? आधिकारिक इमेज का उपयोग करें:

```bash
docker run --rm ghcr.io/migradiff/migra \
  postgres://db_a postgres://db_b
```

---

## GitHub Actions

अपने पुल रिक्वेस्ट वर्कफ़्लो में स्कीमा डिफिंग जोड़ें:

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
```

यदि विनाशकारी संचालन का पता चलता है तो बिल्ड को स्वचालित रूप से विफल करें:

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
    fail_on_destructive: "true"
```

लाइव कनेक्शन के बजाय स्कीमा डंप फ़ाइलों का उपयोग करें:

```yaml
- uses: migradiff/migra@v1
  with:
    base_file: schema_production.sql
    head_file: schema_branch.sql
```

पूर्ण कॉन्फ़िगरेशन विकल्पों के लिए [docs/action-usage.md](docs/action-usage.md) देखें।

---

## Pre-commit हुक

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/migradiff/migra
    rev: v1.1.0
    hooks:
      - id: migra
```

पूर्ण कॉन्फ़िगरेशन विकल्पों के लिए रिपो रूट में `pre-commit-config.example.yaml` देखें।

---

## migra क्या समझता है

- टेबल, कॉलम, बाधाएं, इंडेक्स
- व्यू और मटेरियलाइज्ड व्यू
- फंक्शन और स्टोर्ड प्रोसीजर
- सीक्वेंस
- एनम, कंपोजिट टाइप, डोमेन
- रो-लेवल सिक्योरिटी (RLS) नीतियां
- फॉरेन डेटा रैपर
- कॉलम-लेवल प्रिविलेज
- पार्टीशन टेबल
- ऑब्जेक्ट कमेंट (`COMMENT ON`)

---

## अपस्ट्रीम से सुधार

| क्षेत्र | अपस्ट्रीम (डिप्रीकेटेड) | यह फोर्क |
|---|---|---|
| Python 3.12+ | डिप्रीकेशन वार्निंग | साफ — कोई वार्निंग नहीं |
| RLS नीतियां | आंशिक, समानता बग | पूर्ण CREATE/DROP, पार्टीशन सपोर्ट |
| त्रुटि संदेश | असमर्थित प्रकारों पर अस्पष्ट | ऑब्जेक्ट नाम और इश्यू लिंक के साथ कार्रवाई योग्य |
| --schema फ्लैग | मल्टी-स्कीमा DB में एज केस | अल्पविराम-पृथक, क्रॉस-स्कीमा निर्भरताएं हल |
| pg_dump इनपुट | समर्थित नहीं | प्रथम श्रेणी `--from-file` मोड |
| JSON आउटपुट | समर्थित नहीं | `--output json` जोखिम वर्गीकरण के साथ |
| Docker इमेज | कोई नहीं | `ghcr.io/migradiff/migra` |
| GitHub Action | कोई नहीं | `migradiff/migra-action` |
| Pre-commit हुक | कोई नहीं | `.pre-commit-hooks.yaml` |
| डेव वातावरण | मैनुअल Docker कमांड | `docker compose up -d` |
| AI स्पष्टीकरण | कोई नहीं | Claude के साथ `--explain` फ्लैग — सादी अंग्रेजी डिफ स्पष्टीकरण, जोखिम विश्लेषण, सुरक्षित विकल्प |
| COMMENT ON डिफिंग | समर्थित नहीं | सभी ऑब्जेक्ट प्रकारों पर पूर्ण डिफिंग — जोड़ें/बदलें/हटाएं |

पूर्ण फिक्स इतिहास के लिए [CHANGELOG.md](CHANGELOG.md) देखें।

---

## ज्ञात सीमाएं

migra SQL डिफ जनरेट करता है — इसे लागू नहीं करता। प्रोडक्शन पर चलाने से पहले प्रत्येक जनरेटेड स्क्रिप्ट की समीक्षा करें। विनाशकारी संचालन (`DROP TABLE`, `DROP COLUMN`) JSON आउटपुट मोड में चिह्नित किए जाते हैं लेकिन सादा SQL मोड में अवरुद्ध नहीं किए जाते।

migra को स्कीमा इंट्रोस्पेक्ट करने के लिए लाइव PostgreSQL कनेक्शन, या `--from-file` के माध्यम से स्कीमा डंप फ़ाइलों की आवश्यकता होती है। यह रॉ DDL टेक्स्ट को पार्स नहीं करता।

---

## योगदान सूचना

इस परियोजना में आपकी रुचि के लिए धन्यवाद। कृपया ध्यान दें कि हम वर्तमान में किसी भी बाहरी कोड योगदान, पुल रिक्वेस्ट, बग फिक्स, या फीचर सबमिशन को स्वीकार नहीं कर रहे हैं।

खोले गए किसी भी पुल रिक्वेस्ट को बिना समीक्षा के स्वचालित रूप से बंद कर दिया जाएगा।

---

## लाइसेंसिंग

MigraDiff **मुफ्त और ओपन सोर्स** है, MIT लाइसेंस के तहत।

**सभी सुविधाएं सभी के लिए काम करती हैं।** कोई पेवॉल नहीं, कोई कोड प्रतिबंध नहीं, कोई गेटकीपिंग नहीं।

### एक संक्षिप्त कहानी

मैंने Philips में एक इंजीनियर के रूप में 8+ साल बिताए, अस्पताल के IT सिस्टम को सपोर्ट करते हुए जो मरीजों को सुरक्षित रखते हैं। जब हमारे डिवीजन को अधिग्रहित करने वाले VC ने मुझे नौकरी से निकाल दिया, मैं 50+ साल का था एक बाजार में जहां उम्र मायने रखती है। दूसरी नौकरी ढूंढना लगभग असंभव हो गया। मुझे अभी भी अपने परिवार का समर्थन करना और टेबल पर खाना रखना है।

यही कारण है कि MigraDiff मौजूद है। मैं ऐसे टूल बना रहा हूं जो आपकी मदद करते हैं, क्योंकि इसी तरह मैं नियोजित रहता हूं।

### निवेदन

**यदि आप एक छात्र, शौकिया, या ओपन सोर्स प्रोजेक्ट हैं:** MIT लाइसेंस, हमेशा मुफ्त। किसी समझौते की आवश्यकता नहीं।

**यदि आप MigraDiff का उपयोग करने वाली लाभ-उन्मुख कंपनी हैं:** कृपया एक व्यावसायिक लाइसेंस समझौते पर हस्ताक्षर करें। यह कोड को गेटकीप करने के बारे में नहीं है—हर सुविधा मुफ्त रहती है, आप इसे स्थानीय रूप से चलाते हैं, आपके लिए तकनीकी रूप से कुछ भी नहीं बदलता है। यह निष्पक्षता के बारे में है: यदि मेरा टूल आपको पैसे कमाने में मदद कर रहा है, तो मेरे परिवार को खिलाने में मेरी मदद करें।

आप अभी भी सब कुछ के मालिक हैं। आप अपने डेटा को नियंत्रित करते हैं। आप सभी सुविधाओं तक पहुंचते हैं। हम केवल इस बारे में पारदर्शी हो रहे हैं कि हम विकास को कैसे बनाए रखते हैं।

मैं दान नहीं मांग रहा। मैं निष्पक्षता मांग रहा हूं।

[व्यावसायिक लाइसेंस प्राप्त करें](https://lateos.ai/license) | [MIT लाइसेंस देखें](LICENSE)

---

## आभार

यह प्रोजेक्ट [djrobstep/migra](https://github.com/djrobstep/migra) का फोर्क है, जिसे मूल रूप से Robert Lechte द्वारा बनाया और अनुरक्षित किया गया था। कोर डिफिंग इंजन उनका काम है। हम इसके लिए आभारी हैं।
