# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning

class ListaPrecios(models.Model):
    _name = "lista.precios.megatk"
    _order = 'name asc'

    name = fields.Many2one("lista.precios.tipo.descuento", "Tipo de Precio", required=True, ondelete='cascade')
    descuento = fields.Float(" Porcentaje %")
    company_id = fields.Many2one('res.company', "Empresa", default=lambda self: self.env.user.company_id, required=True)
    detalle_ids = fields.One2many("lista.precios.megatk.line", "obj_padre", "Productos")
    state = fields.Selection([('borrador', 'Borrador'), ('valida', 'Validada'), ('anulada', 'Anulada')], string='Estado', readonly=True, default='borrador')
    precio_ids = fields.One2many("lista.precios.producto", "lista_id", "Precios por productos")
    
    def defaulprecio(self):
        lineas = self.env['account.invoice.line'].search([('precio_id','=',False)])
        for line in lineas:
            preciolista = self.env['lista.precios.producto']
            preciodefaul = preciolista.search( [('product_id.id', '=', line.product_id.product_tmpl_id.id)])
            for lista in preciodefaul:
                porcentaje= (((line.price_unit - line.product_id.list_price)*100)/line.product_id.list_price)
                porcentaje=round(porcentaje,2)
                if porcentaje >= lista.descuento:
                    line.write({'precio_id': lista.id})

    @api.onchange("name")
    def onchangedescuento(self):
        if self.name:
            self.descuento = self.name.descuento

    @api.multi
    def back_draft(self):
        self.write({'state': 'borrador'})

    @api.multi
    def validar_lista(self):
        if self.detalle_ids:
            if self.precio_ids:
                for lis in self.precio_ids:
                    lis.unlink()
            for precio in self.detalle_ids:
                obj_precio = self.env["lista.precios.producto"]
                precio.precio_publico = precio.product_id.list_price
                precio.precio_descuento = precio.precio_publico * (1 + (precio.obj_padre.descuento / 100))
                precio.costo = precio.product_id.standard_price
                if precio.precio_descuento <= precio.product_id.standard_price:
                    raise Warning(_('Este producto tiene precio igual o menor que el precio costo -- %s') % (precio.product_id.name))
                valores = {
                    'name': self.name.id,
                    'lista_id': self.id,
                    'descuento': self.descuento,
                    'precio': precio.precio_descuento,
                    'product_id': precio.product_id.id, 
                }
                id_precio = obj_precio.create(valores)
            self.write({'state': 'valida'})
        else:
            raise Warning(_('No existe productos en la lista de precios'))

    @api.multi
    def unlink(self):
        if not self.state == 'borrador':
            raise Warning(_('No se puede borrar lista de precios validadas'))
        res = super(ListaPrecios, self).unlink()
        return res



class ListaPreciosLine(models.Model):
    _name = "lista.precios.megatk.line"

    obj_padre = fields.Many2one("lista.precios.megatk", "Precio", ondelete='cascade')
    product_id = fields.Many2one("product.template", "Producto", required=True, )
    precio_publico = fields.Float("Precio Base", )
    precio_descuento = fields.Float("Precio de lista", )
    costo = fields.Float("Costo")
    x_descuento = fields.Float(related='obj_padre.descuento', string=" % ")

    @api.onchange("product_id")
    def onchangeproducto(self):
        parent_model = self.env.context.get('parent_id')  
        if self.product_id:
            self.precio_publico = self.product_id.list_price
            self.precio_descuento = self.precio_publico * (1 + (self.obj_padre.descuento / 100))
            if self.precio_descuento < self.product_id.standard_price:
                raise Warning(_('El precio con descuento no debe de ser menor que el precio de costo del producto '))

        
