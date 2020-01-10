# -*- coding: utf-8 -*-
import requests
import json
import amanobot
from amanobot.loop import MessageLoop
from amanobot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
import constants
import time
import sqlite3
import emoji
from datetime import datetime
from pytz import timezone

TOKEN = ''
BASE_NAME = 'banco.healthcheck.db'

def getTimes(tab):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = 'SELECT distinct timestamp,user_id FROM ' + tab + ' ORDER BY timestamp DESC'
		cursor.execute(sql)
		data = cursor.fetchmany(7)
		return data

def getUserResult(timestamp):
	with sqlite3.connect(BASE_NAME) as con:
		cursor = con.cursor()
		sql = ''' 
		select users.user_id, coalesce(s.qtd,0) as qtd_sim, COALESCE(n.qtd,0) as qtd_nao
		from 
			(SELECT DISTINCT user_id from (SELECT DISTINCT user_id from sim union SELECT DISTINCT user_id from nao)) as users
		left outer join
			(select sim.user_id, count(*) as qtd from sim
			inner join pergunta on sim."timestamp" == pergunta."timestamp"	and sim.message_id == pergunta.message_id
			where sim."timestamp" = '''+ timestamp +'''
			group by sim.user_id, sim."timestamp") as s on users.user_id = s.user_id
		left outer join
			(select nao.user_id, count(*) as qtd from nao
			inner join pergunta on nao."timestamp" == pergunta."timestamp"	and nao.message_id == pergunta.message_id
			where nao."timestamp" = '''+ timestamp +'''
			group by nao.user_id, nao."timestamp") as n on users.user_id = n.user_id'''
		cursor.execute(sql)
		data = cursor.fetchall()
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

bot = amanobot.Bot(TOKEN) #healthcheck

stamps = getTimes("pergunta")
chat_log = -1001498194874 #chat para onde enviar resultado


if(len(stamps) == 0):
	bot.sendMessage(chat_log,"Nenhuma pergunta foi feita ainda. Envie /check antes")
else:
	for stamp in stamps:
			
		dataRecuperada = datetime.strptime(stamp[0], "%Y%m%d")
		
		chat_id = stamp[1]
		resultados = getUserResult(stamp[0])

		if(len(resultados) == 0):
			bot.sendMessage(chat_log,"Sem respostas até o momento!")
		else:
			#print(resultados)
			id_usuario_anterior = 0
			msg_result = ''
			flPrintPergunta = False
			for result in resultados:
				user_id = result[0]
				count_sim = result[1]
				count_nao = result[2]
				try:
					user = bot.getChatMember(chat_id,user_id)
				except:
					pass

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
			
			bot.sendMessage(chat_log,msg_result)



