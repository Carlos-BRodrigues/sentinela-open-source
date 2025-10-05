# sentinela-telegram
 Desenvolvido para Agencia Pública, Universidade de Virginia

## Para utilizar esse raspador

1. Faça uma cópia do `config_example.json` e renomeie `config.json`;
2. Configure o endereço da sua base de dados MySQL no arquivo `config.json`;
3. Execute o script `run_configuration.py` e verifique se as tabelas foram criadas;
4. Para conseguir as chaves de API do Telegram, acesse my.telegram.org cadastre o número do aparelho;
5. Peça a criação de uma aplicação Desktop e preencha o formulário informando os objetivos da ferramenta;
6. Preencha o arquivo `config.json` com os detalhes fornecidos (id e hash);
7. Preencha também a tabela no banco de dados referente a esse usuário com o número de telefone e o nome cadastrados em `config.json`;
8. Execute o script `get_groups.py` e em seguida o `get_new_messages.py`;

