import os
import sys
import io
from langchain import hub
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from collections import Counter
from langchain.schema import Document  # Document 클래스 임포트

from dotenv import load_dotenv
load_dotenv()
os.getenv("OPENAI_API_KEY")
os.environ["PWD"] = os.getcwd()

#출력의 인코딩을 utf-8로 설정한다
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# 커스텀 로더 클래스를 사용하여 개별 파일을 로드하면서 오류 처리 및 UTF-8 인코딩 적용
class SafeTextLoader(TextLoader):
    def lazy_load(self):
        try:
            # 파일을 UTF-8 인코딩으로 읽도록 설정
            with open(self.file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return [{'content': text, 'metadata': {'source': self.file_path}}]
        except UnicodeDecodeError:
            print(f"인코딩 오류 발생: {self.file_path}. 파일이 UTF-8이 아닌 인코딩을 사용합니다.")
            return []
        except Exception as e:
            # 기타 오류 발생 시
            print(f"파일 로드 중 오류 발생: {self.file_path} - {e}")
            return []

loader = DirectoryLoader("./bizchat/chat/data", glob="*.txt", loader_cls=SafeTextLoader)
documents = loader.load()
# print("문서의 개수: ", len(documents))

# 'dict'를 'Document' 객체로 변환
documents = [Document(page_content=doc['content'], metadata=doc['metadata']) for doc in documents]

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = text_splitter.split_documents(documents)

# print('분할된 텍스트의 개수: ', len(texts))

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = text_splitter.split_documents(documents)

source_list = []
for i in range(0, len(texts)):
  source_list.append(texts[i].metadata["source"])

element_counts = Counter(source_list)
filtered_counts = {key: value for key, value in element_counts.items() if value >= 2}

# print("2개 이상으로 분할된 문서: ", filtered_counts)
# print("분할된 텍스트의 개수: ", len(documents) + len(filtered_counts))

embedding = OpenAIEmbeddings()
# 벡터스토어를 생성합니다.
vectorstore = FAISS.from_documents(documents=texts, embedding=OpenAIEmbeddings())
retriever = vectorstore.as_retriever()

# print(texts[0])

# query = "신혼부부를 위한 정책을 알려주세요."
# docs = retriever.invoke(query)  # 변경된 메서드 사용
# print("유사도가 높은 텍스트 개수: ", len(docs))
# print("--" * 20)
# print("유사도가 높은 텍스트 중 첫 번째 텍스트 출력: ", docs[0])
# print("--" * 20)
# print("유사도가 높은 텍스트들의 문서 출처: ")
# for doc in docs:
#   print(doc.metadata["source"])
#   pass

from langchain_core.prompts import PromptTemplate

prompt = PromptTemplate.from_template(
    """당신은 질문-답변(Question-Answering)을 수행하는 친절한 AI 어시스턴트입니다. 당신의 임무는 주어진 문맥(context) 에서 주어진 질문(question) 에 답하는 것입니다.
검색된 다음 문맥(context) 을 사용하여 질문(question) 에 답하세요. 만약, 주어진 문맥(context) 에서 답을 찾을 수 없다면, 답을 모른다면 `주어진 정보에서 질문에 대한 정보를 찾을 수 없습니다` 라고 답하세요.
한글로 답변해 주세요. 단, 기술적인 용어나 이름은 번역하지 않고 그대로 사용해 주세요. 답변은 3줄 이내로 요약해 주세요.

#Question: 
{question} 

#Context: 
{context} 

#Answer:"""
)

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

# 체인을 생성합니다.
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

from langchain_teddynote.messages import stream_response

# 출력하여 전달된 인수 확인
# print(f"Arguments received: {sys.argv}")

#  Parse the incoming JSON string argument
# input_data = json.loads(sys.argv[1])
# print(input_data)

sendedQuestion = sys.argv[1]
# print(sendedQuestion)

answer = rag_chain.stream(sendedQuestion)
stream_response(answer)

