// Classe que representa a página de histórico de transações
class HitoryPage {
    // Retorna os seletores usados para validações na página
    selectorsList() {
        const selectors = {
            // Container principal da página, usado para verificar se a página carregou
            checkPage: '.MuiPaper-elevation1',
            // Aba "Mine" (rota /personal) — lista só as transações do próprio usuário
            // logado, imune ao volume/paginação do feed público global (Fase 3.4,
            // correção de fragilidade: transação hardcoded era empurrada para
            // páginas seguintes do feed público conforme a suíte gera mais dados)
            mineTab: "[data-test='nav-personal-tab']",
            // Elemento que representa uma transação específica para clicar
            checkTransaction: "[data-test='transaction-amount-6XY0Ud1i8sp4']",
            // Container que mostra os detalhes da transação após clique
            checkDetails: '.TransactionDetail-paper',
            // Link para contatos, usado no fluxo de visualização falha
            checkFail: "[href='/contacts']",
            // Elemento que indica que não há transações para mostrar
            checkPageFail: "[style='height: 100%; width: 100%;']",
        }
        return selectors
    }

    // Fluxo que simula a visualização bem-sucedida de uma transação
    successfulViewing() {
        // Confirma que a página de histórico foi carregada corretamente
        cy.get(this.selectorsList().checkPage).should('contain', 'Public')

        // Navega para a aba pessoal (Mine/Personal) — lista estável, não sofre
        // com paginação do feed público global
        cy.get(this.selectorsList().mineTab).click()
        cy.get(this.selectorsList().checkPage).should('contain', 'Personal')

        // Clica em uma transação específica
        cy.get(this.selectorsList().checkTransaction).click()

        // Verifica se a página de detalhes da transação foi aberta
        cy.get(this.selectorsList().checkDetails).should('contain', 'Transaction Detail')
    }

    // Fluxo que simula tentativa de visualização falha de transações
    failedViewing() {
        // Confirma que a página de histórico foi carregada corretamente
        cy.get(this.selectorsList().checkPage).should('contain', 'Public')

        // Clica no link de contatos (fluxo alternativo para falha)
        cy.get(this.selectorsList().checkFail).click()

        // Verifica se a página exibe mensagem indicando ausência de transações
        cy.get(this.selectorsList().checkPageFail).should('contain', 'No Transactions')
    }
}

export default HitoryPage