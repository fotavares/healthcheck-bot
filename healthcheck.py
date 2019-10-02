import requests
import json
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
import constants
import time
import sqlite3
#import shortuuid 
from datetime import datetime
from pytz import timezone

count_sim = ''
count_nao = ''


BASE_NAME = 'banco.healthcheck.db'
def insert(tab,user_id, chat_id,message_id,timestamp):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = 'INSERT INTO ' + tab + ' values (?,?,?,?)'
		cursor.execute(sql,[(chat_id),(user_id),(message_id),(timestamp)])
		con.commit()

def insertQuestion(id,perg,timestamp):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = 'INSERT INTO pergunta values (?,?,?,?)'
		cursor.execute(sql,[(0),(id),(perg),(timestamp)])
		con.commit()

def delete(tab,user_id, chat_id,message_id,timestamp):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = 'DELETE FROM ' + tab + ' WHERE chat_id = ? and message_id = ? and user_id = ?  and timestamp = ?'
		cursor.execute(sql,[(chat_id),(message_id),(user_id),(timestamp)])
		con.commit()

def count(tab,user_id, chat_id,message_id):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = ''
		if user_id == None:
			sql = 'SELECT COUNT(*) FROM ' + tab + ' WHERE chat_id = ? and message_id = ?'
			cursor.execute(sql,[(chat_id),(message_id)])
		else:
			sql = 'SELECT COUNT(*) FROM ' + tab + ' WHERE chat_id = ? and message_id = ? and user_id = ?'
			cursor.execute(sql,[(chat_id),(message_id),(user_id)])
		data = cursor.fetchone()
		return int(data[0])

def getTimes(tab):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = 'SELECT distinct timestamp FROM ' + tab + ' ORDER BY timestamp DESC'
		cursor.execute(sql)
		data = cursor.fetchmany(7)
		return data

def getResult(timestamp):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = '''select * from (
		select sim.user_id,sim.message_id, pergunta.question, "Sim" as Resposta, sim."timestamp" from sim
		inner join pergunta on sim."timestamp" == pergunta."timestamp" and sim.message_id == pergunta.message_id
		UNION
		select nao.user_id,nao.message_id, pergunta.question, "Não"  as Resposta, nao."timestamp" from nao
		inner join pergunta on nao."timestamp" == pergunta."timestamp" and nao.message_id == pergunta.message_id
		) where "timestamp" = '''  + timestamp + '''
		order by user_id,message_id'''
		cursor.execute(sql)
		data = cursor.fetchall()
		return data
		
def handle(msg):
	content_type, chat_type, chat_id = telepot.glance(msg)
	#print(msg)

	data = datetime.now(timezone('Brazil/East')).strftime('%Y%m%d')

	keybVoto = InlineKeyboardMarkup(inline_keyboard=[[
					InlineKeyboardButton(text="Sim", callback_data=data+'|sim'),
					InlineKeyboardButton(text="Não", callback_data=data+'|nao'),
	]])

	if '/check' in msg['text']:
		stamps = getTimes("pergunta")
		if(len(stamps) == 0):
			enviada = bot.sendMessage(chat_id,"Você dormiu mais de 6 horas por noite a cada dia nessa semana?",reply_markup=keybVoto)
			insertQuestion(enviada['message_id'],enviada['text'],data)
			enviada = bot.sendMessage(chat_id,"Você praticou alguma atividade física em ao menos 1 dia essa semana?",reply_markup=keybVoto)
			insertQuestion(enviada['message_id'],enviada['text'],data)
			enviada = bot.sendMessage(chat_id,"Você fez algo que te dá muito prazer, fora trabalho, em ao menos um dia essa semana?",reply_markup=keybVoto)
			insertQuestion(enviada['message_id'],enviada['text'],data)
			enviada = bot.sendMessage(chat_id,"Você teve algum momento de autocuidado (relacionado à auto estima, beleza etc) em ao menos um dia essa semana?",reply_markup=keybVoto)
			insertQuestion(enviada['message_id'],enviada['text'],data)
		else:
			if(str(data) not in stamps[0]):
				enviada = bot.sendMessage(chat_id,"Você dormiu mais de 6 horas por noite a cada dia nessa semana?",reply_markup=keybVoto)
				insertQuestion(enviada['message_id'],enviada['text'],data)
				enviada = bot.sendMessage(chat_id,"Você praticou alguma atividade física em ao menos 1 dia essa semana?",reply_markup=keybVoto)
				insertQuestion(enviada['message_id'],enviada['text'],data)
				enviada = bot.sendMessage(chat_id,"Você fez algo que te dá muito prazer, fora trabalho, em ao menos um dia essa semana?",reply_markup=keybVoto)
				insertQuestion(enviada['message_id'],enviada['text'],data)
				enviada = bot.sendMessage(chat_id,"Você teve algum momento de autocuidado (relacionado à auto estima, beleza etc) em ao menos um dia essa semana?",reply_markup=keybVoto)
				insertQuestion(enviada['message_id'],enviada['text'],data)
			else:
				bot.sendMessage(chat_id,"Já foi enviada uma enquete hoje")

	if '/result' in msg['text'] :
		keyboard = []
		stamps = getTimes("pergunta")
		for s in stamps:
			dataRecuperada = datetime.strptime(s[0], "%Y%m%d")

			keyboard = keyboard + [[InlineKeyboardButton(text=dataRecuperada.strftime("%d/%m/%Y"), callback_data=s[0]+"|result")]]
		keybResult = InlineKeyboardMarkup(inline_keyboard=keyboard)
		bot.sendMessage(chat_id, "Escolha a data para o resultado:",reply_markup=keybResult)
	
	

def callback(msg):
	query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
	#print(msg)
	message_id = msg['message']['message_id']
	chat_id = msg['message']['chat']['id']

	data = query_data.split('|')
	timestamp = data[0]

	if data[1] == 'sim' or data[1] == 'nao':
		if data[1] == 'sim':
			if count('sim',from_id, chat_id,message_id) == 0:
				delete('nao',from_id, chat_id,message_id,timestamp)
				insert('sim',from_id, chat_id,message_id,timestamp)
			else:
				delete('sim',from_id, chat_id,message_id,timestamp)
		if data[1] == 'nao':
			if count('nao',from_id, chat_id,message_id) == 0:
				delete('sim',from_id, chat_id,message_id,timestamp)
				insert('nao',from_id, chat_id,message_id,timestamp)
			else:
				delete('nao',from_id, chat_id,message_id,timestamp)

		bot.answerCallbackQuery(query_id,"Votado!")
		count_sim = count('sim',None, chat_id,message_id)
		count_nao = count('nao',None, chat_id,message_id)

		keybVoto = InlineKeyboardMarkup(inline_keyboard=[[
						InlineKeyboardButton(text='Sim' +' '+ str(count_sim), callback_data=timestamp+'|sim'),
						InlineKeyboardButton(text='Não' + ' ' + str(count_nao), callback_data=timestamp+'|nao'),
		]])
		ident_mensagem = (chat_id,message_id)
		bot.editMessageReplyMarkup(ident_mensagem, reply_markup=keybVoto)

	if data[1] == 'result':
		resultados = getResult(timestamp)
		print(resultados)
		id_usuario_anterior = 0
		msg_result = ''
		for result in resultados:
			user_id = result[0]
			text = result[2]
			resp = result[3]
			user = bot.getChatMember(chat_id,user_id)

			if(id_usuario_anterior != user_id):
				msg_result = msg_result + '\n*' + user['user']['first_name'] + ' ('+user['user']['username']+')*\n'
			msg_result = msg_result + '      '+text + ' _' + resp +'_\n'
			id_usuario_anterior = user_id
		
		bot.sendMessage(chat_id,msg_result,parse_mode="Markdown")



bot = telepot.Bot(TOKEN)
MessageLoop(bot, {'chat':handle,
				  'callback_query':callback}).run_as_thread()

print ('I am listening ...')

while 1:
	time.sleep(10)


