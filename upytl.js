upytl = {}

upytl.mount_component = function(id, data){
    data = data || {}
    var id = `#${id}`
    var c = Vue.extend({template: id, data: ()=>data})
    new c().$mount(id)
}