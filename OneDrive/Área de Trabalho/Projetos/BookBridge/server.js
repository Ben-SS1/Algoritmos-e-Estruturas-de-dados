import express from "express"
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const app = express();

app.use(express.json());

const users = [];

app.post('/usuarios', async (req, res) => {
    await prisma.user.create({
        data: {
            email: req.body.email,
            name: req.body.name,
            age: req.body.age
        }
    })

    res.status(201).json(req.body);
});

app.get('/usuarios', (req, res) => {
    res.status(200).json(users);
});

app.listen(3000);

/* Cadastro de usuários (CRUD completo), 
 criação de clubes de leitura (CRUD completo),
 adição de livros (CRUD Completo)
 adição de livros a lista de leitura do clube
 registro de opiniões sobre os livros 
 Utilizar um sistema de autenticação para garantir a segurança dos dados dos usuários 
 e fornecer estatisticas basicas sobre as leituras*/