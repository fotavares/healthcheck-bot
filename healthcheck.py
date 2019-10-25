# -*- coding: utf-8 -*-
import requests
import json
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
import constants
import time
import sqlite3
import emoji
from datetime import datetime
from pytz import timezone
import os
import sys
import psutil

count_sim = ''
count_nao = ''

BOT_ADMIN = ''

BASE_NAME = 'banco.healthcheck.db'
def insert(tab,user_id, chat_id,message_id,timestamp):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = 'INSERT INTO ' + tab + ' values (?,?,?,?)'
		cursor.execute(sql,[(chat_id),(user_id),(message_id),(timestamp)])
		con.commit()

def insertQuestion(id,perg,timestamp,chat_id):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = 'INSERT INTO pergunta values (?,?,?,?)'
		cursor.execute(sql,[(chat_id),(id),(perg),(timestamp)])
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

def getTimes(chat_id):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = 'SELECT distinct timestamp FROM pergunta where user_id = '+ str(chat_id) +' ORDER BY timestamp DESC'
		cursor.execute(sql)
		data = cursor.fetchmany(7)
		return data

def getUserResult(timestamp,chat_id):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = ''' 
		select users.user_id, coalesce(s.qtd,0) as qtd_sim, COALESCE(n.qtd,0) as qtd_nao
		from 
			(SELECT DISTINCT user_id from (SELECT DISTINCT user_id from sim where chat_id = ''' + str(chat_id) + ''' 
											union 
											SELECT DISTINCT user_id from nao where chat_id = ''' + str(chat_id) + ''')) as users
		left outer join
			(select sim.user_id, count(*) as qtd from sim
			inner join pergunta on sim."timestamp" == pergunta."timestamp"	and sim.message_id == pergunta.message_id and sim.chat_id == pergunta.user_id
			where sim."timestamp" = '''+ timestamp +''' and chat_id = ''' + str(chat_id) + '''
			group by sim.user_id, sim."timestamp") as s on users.user_id = s.user_id
		left outer join
			(select nao.user_id, count(*) as qtd from nao
			inner join pergunta on nao."timestamp" == pergunta."timestamp"	and nao.message_id == pergunta.message_id and nao.chat_id == pergunta.user_id
			where nao."timestamp" = '''+ timestamp +''' and chat_id = ''' + str(chat_id) + '''
			group by nao.user_id, nao."timestamp") as n on users.user_id = n.user_id'''
		cursor.execute(sql)
		data = cursor.fetchall()
		#print(data)
		return data

def getChats():
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = 'SELECT distinct user_id FROM pergunta '
		cursor.execute(sql)
		data = cursor.fetchall()
		#print(data)
		return data

def getEmojiResult(qtd):
	txtReturn = ''
	if(qtd == 4): 
		txtReturn = emoji.emojize(":heart:", use_aliases=True)
	elif(qtd == 3): 	
		txtReturn = emoji.emojize(":expressionless:", use_aliases=True)
	elif(qtd == 2): 
		txtReturn = emoji.emojize(":pensive:", use_aliases=True)
	elif(qtd == 1): 
		txtReturn = emoji.emojize(":face_with_head-bandage:", use_aliases=True)
	elif(qtd == 0): 
		txtReturn = emoji.emojize(":skull_and_crossbones:", use_aliases=True)
	return txtReturn

def EnviaPerguntas(chat_id):
	data = datetime.now(timezone('Brazil/East')).strftime('%Y%m%d')

	keybVoto = InlineKeyboardMarkup(inline_keyboard=[[
			InlineKeyboardButton(text="Sim", callback_data=data+'|sim'),
			InlineKeyboardButton(text="Não", callback_data=data+'|nao'),
	]])

	stamps = getTimes(chat_id)
	send_question = True if (len(stamps) == 0) else True if (str(data) not in stamps[0]) else False
	if (send_question):
		enviada = bot.sendMessage(chat_id,"Você dormiu mais de 6 horas por noite a cada dia nessa semana?",reply_markup=keybVoto)
		insertQuestion(enviada['message_id'],enviada['text'],data,chat_id)
		enviada = bot.sendMessage(chat_id,"Você praticou alguma atividade física em ao menos 1 dia essa semana?",reply_markup=keybVoto)
		insertQuestion(enviada['message_id'],enviada['text'],data,chat_id)
		enviada = bot.sendMessage(chat_id,"Você fez algo que te dá muito prazer, fora trabalho, em ao menos um dia essa semana?",reply_markup=keybVoto)
		insertQuestion(enviada['message_id'],enviada['text'],data,chat_id)
		enviada = bot.sendMessage(chat_id,"Você teve algum momento de autocuidado (relacionado à auto estima, beleza etc) em ao menos um dia essa semana?",reply_markup=keybVoto)
		insertQuestion(enviada['message_id'],enviada['text'],data,chat_id)
	else:
		bot.sendMessage(chat_id,"Já foi enviada uma enquete hoje")

def CarregaRespostas(chat_id):
	stamps = getTimes(chat_id)
	if(len(stamps) == 0):
		bot.sendMessage(chat_id,"Nenhuma pergunta foi feita ainda. Envie /check antes")
	else:
		dataRecuperada = datetime.strptime(stamps[0][0], "%Y%m%d")
		
		resultados = getUserResult(stamps[0][0],chat_id)
		if(len(resultados) == 0):
			bot.sendMessage(chat_id,"Sem respostas até o momento!")
		else:
			#print(resultados)
			id_usuario_anterior = 0
			msg_result = ''
			flPrintPergunta = False
			for result in resultados:
				user_id = result[0]
				count_sim = result[1]
				count_nao = result[2]
				user = bot.getChatMember(chat_id,user_id)

				if not flPrintPergunta:
					msg_result = msg_result + dataRecuperada.strftime("%d/%m/%Y") + '\n\n'
					msg_result = msg_result + "Resultado Healthcheck: " + ' \n'
					msg_result = msg_result + getEmojiResult(4)+ " - 4 sim / 0 nao " + ' \n'
					msg_result = msg_result + getEmojiResult(3)+ " - 3 sim / 1 nao " + ' \n'
					msg_result = msg_result + getEmojiResult(2)+ " - 2 sim / 2 nao " + ' \n'
					msg_result = msg_result + getEmojiResult(1)+ " - 1 sim / 3 nao " + ' \n'
					msg_result = msg_result + getEmojiResult(0)+ " - 0 sim / 4 nao " + ' \n'

					flPrintPergunta = True

				if(id_usuario_anterior != user_id):
					if(count_sim != 0) or (count_nao != 0):
						msg_result = msg_result + '\n' + user['user']['first_name'] + ' ('+user['user']['username']+') :  ' + getEmojiResult(count_sim) 
				id_usuario_anterior = user_id
			
			bot.sendMessage(chat_id,msg_result)


def handle(msg):
	content_type, chat_type, chat_id = telepot.glance(msg)
	#print(msg)

	#Privado
	if chat_type == 'private':
		if msg['from']['username'] == BOT_ADMIN:
			if 'text' in msg:
				if msg['text'] == '/restart':
					try:
						p = psutil.Process(os.getpid())
						for handler in p.open_files() + p.connections():
							os.close(handler.fd)
						python = sys.executable
						os.execl(python, python, *sys.argv)
					except Exception as e:
						print("Erro ao reiniciar processo")
	

	if '/check' in msg['text']:
		EnviaPerguntas(chat_id)

	if '/result' in msg['text']:
		CarregaRespostas(chat_id)
	
	

def callback(msg):
	query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
	#print(msg)
	message_id = msg['message']['message_id']
	chat_id = msg['message']['chat']['id']

	refreshButton = False
	data = query_data.split('|')
	timestamp = data[0]

	if data[1] == 'sim' or data[1] == 'nao':
		if data[1] == 'sim':
			if count('sim',from_id, chat_id,message_id) == 0:
				delete('nao',from_id, chat_id,message_id,timestamp)
				insert('sim',from_id, chat_id,message_id,timestamp)
				bot.answerCallbackQuery(query_id,"Votado!")
				refreshButton = True
			else:
				bot.answerCallbackQuery(query_id,"Você já votou nessa opção!")

		if data[1] == 'nao':
			if count('nao',from_id, chat_id,message_id) == 0:
				delete('sim',from_id, chat_id,message_id,timestamp)
				insert('nao',from_id, chat_id,message_id,timestamp)
				bot.answerCallbackQuery(query_id,"Votado!")
				refreshButton = True
			else:
				bot.answerCallbackQuery(query_id,"Você já votou nessa opção!")
		
		count_sim = count('sim',None, chat_id,message_id)
		count_nao = count('nao',None, chat_id,message_id)

		keybVoto = InlineKeyboardMarkup(inline_keyboard=[[
						InlineKeyboardButton(text='Sim' +' '+ str(count_sim), callback_data=timestamp+'|sim'),
						InlineKeyboardButton(text='Não' + ' ' + str(count_nao), callback_data=timestamp+'|nao'),
		]])
		ident_mensagem = (chat_id,message_id)
		if(refreshButton):
			bot.editMessageReplyMarkup(ident_mensagem, reply_markup=keybVoto)

	
bot = telepot.Bot('') #healthcheck 
if len(sys.argv) > 1:
	if(sys.argv[1]) == 'Pergunta':
		for chat_id in getChats():
			try:
				#print(chat_id[0])
				bot.sendChatAction(chat_id[0],'typing')
			except:
				print(chat_id[0] + " indisponível")
				pass
			else:
				EnviaPerguntas(chat_id[0])
				print("Mensagem Enviada via Cron")
	elif (sys.argv[1]) == 'Resposta':
		for chat_id in getChats():
			try:
				#print(chat_id[0])
				bot.sendChatAction(chat_id[0],'typing')
			except:
				print(chat_id[0] + " indisponível")
				pass
			else:
				CarregaRespostas(chat_id[0])
else:
	MessageLoop(bot, {'chat':handle,
					'callback_query':callback}).run_as_thread()

	print ('Executando HealthCheck...')

	while 1:
		time.sleep(10)


