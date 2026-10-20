import os, tempfile, unittest, sys, threading, json, urllib.request, urllib.error
from pathlib import Path
from unittest.mock import patch
TMP=tempfile.TemporaryDirectory()
os.environ['STUDY_DATA']=TMP.name
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

class StudyTests(unittest.TestCase):
    def setUp(self):
        with app.connect() as c:c.execute('DELETE FROM docs');c.execute('DELETE FROM chunks')
    def test_import_search_citation_and_dedup(self):
        raw=b'# Notes\n<!-- page: 1 -->\nSLA uses photopolymers and ultraviolet light.\n<!-- page: 2 -->\nFDM extrudes melted thermoplastic.'
        app.import_file('notes.md',raw);app.import_file('notes.md',raw)
        hits=app.search('FDM thermoplastic')
        self.assertEqual(hits[0]['page'],2)
        self.assertIn('extrudes',hits[0]['text'])
        with app.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM docs').fetchone()[0],1)
    def test_empty_library_can_answer_without_invented_sources(self):
        with patch.object(app,'model_request',return_value={'message':{'content':'答案：B。依据来源：模型知识。'}}) as request:
            r=app.answer('Which is 2+2? A.3 B.4','ollama','local','单选题')
        self.assertTrue(r['generated']);self.assertEqual(r['sources'],[]);self.assertEqual(r['basis'],'general')
        self.assertIn('无匹配课程资料',request.call_args.args[2]['messages'][1]['content'])
    def test_model_adapter_and_prompt(self):
        app.import_file('notes.txt',b'SLA uses ultraviolet light.')
        with patch.object(app,'model_request',return_value={'message':{'content':'SLA uses UV [1].'}}) as mock:
            r=app.answer('SLA: A. resin B. wire','ollama','test-local','单选题')
            self.assertTrue(r['generated']);self.assertIn('[1]',r['answer'])
            self.assertIn('notes.txt',mock.call_args.args[2]['messages'][1]['content'])
    def test_stream_preserves_deltas_and_completion(self):
        import io
        events=[]
        packets=[{'message':{'content':'第一段'}},{'message':{'content':'第二段'}},{'done':True,'done_reason':'length'}]
        wire=io.BytesIO(('\n'.join(json.dumps(p) for p in packets)+'\n').encode())
        with patch('app.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=wire
            text,reason=app.model_stream('ollama',{},events.append)
        self.assertEqual(text,'第一段第二段');self.assertEqual(reason,'length')
        self.assertEqual([e['text'] for e in events],['第一段','第二段'])
    def test_generate_stream_reads_response_field(self):
        import io
        events=[]
        wire=io.BytesIO(b'{"response":"READY"}\n{"done":true,"done_reason":"stop"}\n')
        with patch('app.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=wire
            text,reason=app.model_stream('ollama',{'raw':True},events.append)
            self.assertTrue(opener.return_value.open.call_args.args[0].full_url.endswith('/api/generate'))
        self.assertEqual(text,'READY');self.assertEqual(reason,'stop')
    def test_stream_disconnect_is_not_reported_complete(self):
        import io
        events=[]
        wire=io.BytesIO(b'{"message":{"content":"partial"}}\n')
        with patch('app.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=wire
            with self.assertRaises(ValueError):app.model_stream('ollama',{},events.append)
        self.assertEqual(events[0]['text'],'partial')
    def test_http_stream_protocol(self):
        app.import_file('notes.txt',b'SLA uses ultraviolet light.')
        server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        old=app.PORT;app.PORT=server.server_port
        def fake(provider,payload,emit):
            self.assertTrue(payload['stream'])
            self.assertFalse(payload['think'])
            self.assertTrue(payload['raw'])
            self.assertTrue(payload['prompt'].endswith('</think>\n\n'))
            emit({'type':'token','text':'UV [1]'})
            return 'UV [1]','stop'
        try:
            req=urllib.request.Request(f'http://127.0.0.1:{app.PORT}/api/ask-stream',data=json.dumps({'question':'SLA','provider':'ollama','model':'qwen3-vl:8b'}).encode(),headers={'Content-Type':'application/json'})
            with patch.object(app,'model_stream',side_effect=fake):
                with urllib.request.urlopen(req) as r: events=[json.loads(line) for line in r]
            self.assertEqual(events[0]['type'],'sources')
            self.assertIn('token',[e['type'] for e in events])
            self.assertEqual(events[-1]['type'],'done')
            self.assertEqual(events[-1]['answer'],'UV [1]')
        finally:server.shutdown();server.server_close();app.PORT=old
    def test_invalid_images_rejected(self):
        with self.assertRaises(ValueError):app.validate_images(['garbage'])
        with self.assertRaises(ValueError):app.validate_images(['a','b','c'])
    def test_image_payload_binds_images_to_user_message(self):
        with patch.object(app,'model_request',return_value={'capabilities':['vision']}):
            payload=app.build_payload('ollama','qwen3-vl:8b','system','question',['encoded1','encoded2'])
        self.assertEqual(payload['images'],['encoded1','encoded2'])
        self.assertIn('<|im_start|>user\n[img-0]\n[img-1]',payload['prompt'])
        self.assertTrue(payload['raw']);self.assertEqual(payload['options']['num_ctx'],8192)
    def test_nonvision_model_rejected_for_images(self):
        with patch.object(app,'model_request',return_value={'capabilities':['completion']}):
            with self.assertRaises(ValueError):app.build_payload('ollama','text-only','s','q',['image'])
    def test_text_budget_is_reserved_for_images_and_answer(self):
        with self.assertRaises(ValueError):app.build_payload('ollama','qwen3-vl:8b','s','题'*2000,['a','b'])
    def test_image_only_question_and_no_image_files_saved(self):
        from PIL import Image
        import io,base64
        raw=io.BytesIO();Image.new('RGB',(80,40),'white').save(raw,format='PNG')
        before=set(app.DATA.iterdir())
        with patch.object(app,'model_request',return_value={'capabilities':['vision']}),patch.object(app,'model_stream',return_value=('答案：B','stop')) as stream:
            r=app.answer('','ollama','qwen3-vl:8b','单选题',emit=lambda e:None,images=[base64.b64encode(raw.getvalue()).decode()])
        self.assertEqual(r['answer'],'答案：B');self.assertIn('images',stream.call_args.args[1])
        self.assertEqual(before,set(app.DATA.iterdir()))
    def test_image_question_with_library_uses_transcribed_terms(self):
        from PIL import Image
        import io,base64
        raw=io.BytesIO();Image.new('RGB',(80,40),'white').save(raw,format='PNG')
        app.import_file('notes.txt',b'SLA uses ultraviolet light and photopolymers.')
        with patch.object(app,'model_request',return_value={'capabilities':['vision']}),patch.object(app,'invoke',side_effect=[('Which process uses ultraviolet light? A. SLA B. FDM','stop'),('答案：A [1]','stop')]):
            r=app.answer('','ollama','qwen3-vl:8b','单选题',images=[base64.b64encode(raw.getvalue()).decode()])
        self.assertEqual(r['basis'],'course');self.assertEqual(r['sources'][0]['name'],'notes.txt')
    def test_invalid_page_markers(self):
        with self.assertRaises(ValueError):app.import_file('bad.md',b'<!-- page: 3 -->\nhello')
    def test_markdown_pdf_page_headings_preserve_citations(self):
        raw=('''# Course notes\n## 逐页目录\n- [PDF 第001页](#pdf-page-001)\n'''
             '''<a id="pdf-page-001"></a>\n## PDF 第001页：SLA\nSLA uses photopolymers.\n'''
             '''<a id="pdf-page-002"></a>\n## PDF 第 2 页：FDM\nFDM extrudes thermoplastic.\n'''
             '''### 原页图像\n![page](assets/page-002.jpg)\n''').encode()
        result=app.import_file('course.md',raw)
        self.assertEqual((result['pages'],result['page_kind']),(2,'pdf_page'))
        hits=app.search('FDM thermoplastic')
        self.assertEqual(hits[0]['page'],2)
        self.assertNotIn('assets/',hits[0]['text'])
        self.assertNotIn('逐页目录',hits[0]['text'])
    def test_markdown_missing_pdf_page_rejected(self):
        raw='## PDF 第001页：A\nA\n## PDF 第003页：C\nC'.encode()
        with self.assertRaisesRegex(ValueError,'PDF 页码标题'):app.import_file('broken.md',raw)
    def test_nonlocal_provider_rejected(self):
        with self.assertRaises(ValueError):app.model_request('remote','/api/tags')
    def test_http_host_guard(self):
        server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        old=app.PORT;app.PORT=server.server_port
        try:
            url=f'http://127.0.0.1:{app.PORT}'
            with urllib.request.urlopen(url+'/api/library') as r:self.assertEqual(json.load(r),[])
            req=urllib.request.Request(url+'/api/library',headers={'Host':'evil.example'})
            with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(req)
            self.assertEqual(err.exception.code,403)
        finally:server.shutdown();server.server_close();app.PORT=old

if __name__=='__main__':unittest.main()
