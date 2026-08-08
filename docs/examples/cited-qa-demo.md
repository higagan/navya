# Phase 0 demo: cited Q&A from OCR'd chunks only

This is a hand-run demo of what the "Ask" feature should produce: an answer built
*only* from the JSON chunks in this folder, with every claim traceable to an exact
page. In the real app this retrieval+citation step is automatic (RAG over the
chunk DB); here I did it manually to prove the citation mechanism is sound before
building it.

---

**Q: गादाधरी और बालादेवी टीका में "परिकर" पद का क्या अर्थ लिया गया है, और दोनों में क्या अंतर है?**
(What meaning does "parikara" carry in Gādādharī vs Bālādevī, and how do they differ?)

**A:**
दोनों टीकाकार परिकर को "व्याप्तिपक्षधर्मता" (vyāpti + pakṣadharmatā के समुदाय) के रूप में
लेते हैं, पर उनका तर्क अलग है:

- **गादाधरी** के अनुसार परिकर का प्रयोजन है — दुष्टहेतु में स्मृतत्व के प्रसङ्ग को
  निर्वाह करने के लिए एक ऐसा गुण चाहिए जो निरूप्य हो पर मुक्तकर्मेण (अपने आप) सिद्ध न हो।
  *[Sāmānyanirukti, printed p. ६ / PDF p. 40, Gādādharī]*

- **बालादेवी** इसे और तर्कसंगत बनाते हुए दिखाते हैं कि क्यों केवल "व्याप्ति" या केवल
  "पक्षधर्मता" काफी नहीं — जैसे हृदो वह्निमान् जलात् जैसे उदाहरण में पक्षधर्मत्व के
  अभाव से व्यभिचार अनिवार्य हो जाता, इसलिए दोनों (व्याप्ति + पक्षधर्मता) का साथ ग्रहण
  आवश्यक है। वे "अवच्छेदकावच्छेदेन निरूपणं प्रति अवच्छेदकावच्छेदेन सङ्गतिः" के नियम से
  इसे सिद्ध करते हैं, और आगे (अगले पृष्ठ पर) इसे "अवाधितत्वाभावरूप सङ्गति" कहकर व्यभिचार
  की आशंका को भी हल करते हैं।
  *[Sāmānyanirukti, printed p. ६–७ / PDF p. 40–41, Bālādevī]*

- **विमलप्रभा**, तीसरी टीका, इन दोनों पदों ("दुष्टहेतु", "सप्तम्यर्थ", "प्रसङ्गसङ्गति")
  की शब्दशः व्याख्या करती है — यह गादाधरी और बालादेवी दोनों के तर्क को पदच्छेद करके
  स्पष्ट करने का काम करती है।
  *[Sāmānyanirukti, printed p. ७ / PDF p. 41, Vimalaprabhā]*

---

Every citation above resolves to a specific `{pdf_page, printed_page, layer}` tuple
that a reader can click through to the source scan
(`ocr-experiment/pages/samanyanirukti/page-0XX.png`). This is the exact behavior
that ChatGPT/Gemini can't currently give — because they don't retain a page-indexed
store, they'd guess "page 6" without knowing if that's PDF-page-6 or printed-page-6,
and with no image to verify against.
